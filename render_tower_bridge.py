"""Reproducible rendering, resumable frame caches, encoding and verification."""
import hashlib
import json
import struct
import sys
import time
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'Tower_Bridge'
CONFIG = ROOT / 'config' / 'scene.json'
cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
FPS = int(cfg['fps'])
COUNT = int(FPS * cfg['duration_seconds'])
WIDTH, HEIGHT = int(cfg['render']['width']), int(cfg['render']['height'])
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['stills']
mode = args[0]
profile = 'preview' if mode == 'preview' else 'final'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def identity(profile='final'):
    return {'scene_sha256': sha(OUT / 'Tower_Bridge.blend'),
            'config_sha256': sha(CONFIG), 'profile': profile,
            'fps': FPS, 'frames': COUNT, 'size': [WIDTH, HEIGHT],
            'blender_version': bpy.app.version_string}

def cache(profile):
    data = identity(profile)
    key = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:20]
    directory = ROOT / 'research' / 'render_runs' / key
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / 'manifest.json'
    if manifest.exists():
        assert json.loads(manifest.read_text()) == data, 'Incompatible frame cache'
    else:
        manifest.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return directory

def png_size(path):
    with path.open('rb') as stream:
        header = stream.read(24)
    assert header[:8] == b'\x89PNG\r\n\x1a\n' and len(header) == 24, f'Invalid PNG: {path}'
    return list(struct.unpack('>II', header[16:24]))

def engine(scene, still=False):
    if still:
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = max(16, int(cfg['render'].get('samples', 16)))
        scene.cycles.use_denoising = True
        scene.cycles.device = 'CPU'
        # GPU preferences are optional and never prevent rendering on CPU.
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            for backend in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
                try:
                    prefs.compute_device_type = backend
                    prefs.get_devices()
                    devices = [d for d in prefs.devices if d.type != 'CPU']
                    if devices:
                        for device in prefs.devices:
                            device.use = device in devices
                        scene.cycles.device = 'GPU'
                        break
                except Exception:
                    continue
        except Exception:
            pass
    else:
        for name in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
            try:
                scene.render.engine = name
                break
            except (TypeError, ValueError):
                continue
        else:
            scene.render.engine = 'CYCLES'
            scene.cycles.device = 'CPU'
            scene.cycles.samples = 8
        if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
            scene.eevee.taa_render_samples = int(cfg['render'].get('samples', 16))
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = int(cfg['render'].get('preview_scale', 25)) if profile == 'preview' else 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.fps = FPS

def select_frame(scene, frame):
    scene.frame_set(frame)
    # Explicitly apply camera cuts even during independent still renders.
    markers = sorted((m for m in scene.timeline_markers if m.camera and m.frame <= frame), key=lambda m: m.frame)
    if markers:
        scene.camera = markers[-1].camera
    bpy.context.view_layer.update()

def render(scene, path):
    scene.render.filepath = str(path)
    try:
        bpy.ops.render.render(write_still=True)
    except RuntimeError:
        if scene.render.engine != 'CYCLES' or scene.cycles.device != 'GPU':
            raise
        scene.cycles.device = 'CPU'
        bpy.ops.render.render(write_still=True)

bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Tower_Bridge.blend'))
s = bpy.context.scene
if mode == 'validate':
    from scene_components.validation import validate
    validate(s, OUT)
elif mode == 'stills':
    engine(s, still=True)
    (OUT / 'renders').mkdir(parents=True, exist_ok=True)
    shots = [('Open', COUNT // 2, '01 | Hero camera'), ('Closed', 1, '01 | Hero camera'),
             ('City', COUNT // 4, '05 | City camera'), ('Water', COUNT // 2, '06 | Water camera'),
             ('Evening', COUNT, '07 | Evening camera'), ('Detail', COUNT // 2, '02 | Architectural detail')]
    for name, frame, camera in shots:
        select_frame(s, frame)
        s.camera = bpy.data.objects[camera]
        render(s, OUT / 'renders' / f'Tower_Bridge_{name}.png')
        print('STILL_OK', name, flush=True)
elif mode in ('animation', 'preview', 'benchmark'):
    engine(s)
    directory = cache(profile)
    expected = [WIDTH * s.render.resolution_percentage // 100, HEIGHT * s.render.resolution_percentage // 100]
    if mode == 'benchmark':
        frames = [1, COUNT // 2, COUNT]
    else:
        start = int(args[1]) if len(args) > 1 else 1
        end = int(args[2]) if len(args) > 2 else COUNT
        assert 1 <= start <= end <= COUNT
        frames = range(start, end + 1)
    timings = []
    for frame in frames:
        path = directory / f'{frame:04d}.png'
        if mode != 'benchmark' and path.exists():
            assert png_size(path) == expected, f'Corrupt cached frame: {path}'
            continue
        started = time.perf_counter()
        select_frame(s, frame)
        render(s, path)
        assert png_size(path) == expected
        seconds = time.perf_counter() - started
        timings.append({'frame': frame, 'seconds': seconds})
        if mode == 'benchmark' or frame % FPS == 0:
            print('FRAME_OK', frame, COUNT, round(seconds, 3), flush=True)
    if mode == 'benchmark':
        report = {'identity': identity(), 'timings': timings, 'engine': s.render.engine}
        try:
            import resource
            report['peak_rss_platform_units'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except ImportError:
            report['memory_note'] = 'Peak RSS is unavailable through Python resource on this platform.'
        (OUT / 'benchmark.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
elif mode in ('encode', 'video_check'):
    target = OUT / 'Tower_Bridge_Animation.mp4'
    signature = identity()
    if mode == 'encode':
        directory = cache('final')
        for frame in range(1, COUNT + 1):
            path = directory / f'{frame:04d}.png'
            assert path.is_file(), f'Missing frame: {path}'
            assert png_size(path) == [WIDTH, HEIGHT], f'Wrong frame dimensions: {path}'
    else:
        report = json.loads((OUT / 'video_validation.json').read_text())
        assert report['identity'] == signature, 'Video belongs to an earlier scene/configuration'
        assert report['video_sha256'] == sha(target), 'Video hash mismatch'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = WIDTH, HEIGHT
    s.render.resolution_percentage = 100
    s.render.fps = FPS
    s.frame_start, s.frame_end = 1, COUNT
    s.render.use_sequencer = True
    s.view_settings.view_transform = 'Standard'
    seq = s.sequence_editor_create()
    collection = seq.strips if hasattr(seq, 'strips') else seq.sequences
    if mode == 'encode':
        strip = collection.new_image('Tower Bridge animation', str(directory / '0001.png'), channel=1, frame_start=1)
        for frame in range(2, COUNT + 1):
            strip.elements.append(f'{frame:04d}.png')
        strip.frame_final_duration = COUNT
        assert len(strip.elements) == COUNT
        try:
            s.render.image_settings.file_format = 'FFMPEG'
        except TypeError:
            s.render.image_settings.media_type = 'VIDEO'
            s.render.image_settings.file_format = 'FFMPEG'
        s.render.ffmpeg.format = 'MPEG4'
        s.render.ffmpeg.codec = 'H264'
        s.render.ffmpeg.constant_rate_factor = 'HIGH'
        s.render.ffmpeg.ffmpeg_preset = 'GOOD'
        s.render.filepath = str(target)
        bpy.ops.render.render(animation=True)
    else:
        collection.new_movie('Decoded finished MP4', str(target), channel=1, frame_start=1)
        s.render.image_settings.file_format = 'PNG'
        decoded = []
        for frame in [1, COUNT // 6, COUNT // 3, COUNT // 2, COUNT * 2 // 3, COUNT * 5 // 6, COUNT]:
            s.frame_set(frame)
            path = ROOT / 'research' / f'video_decoded_{frame:04d}.png'
            render(s, path)
            assert png_size(path) == [WIDTH, HEIGHT]
            decoded.append(frame)
        report['decoded_frames'] = decoded
        (OUT / 'video_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    clip = bpy.data.movieclips.load(str(target), check_existing=False)
    info = {'frames': clip.frame_duration, 'size': list(clip.size), 'fps': clip.fps,
            'bytes': target.stat().st_size, 'video_sha256': sha(target), 'identity': signature}
    assert info['frames'] == COUNT and info['size'] == [WIDTH, HEIGHT], info
    assert abs(info['fps'] - FPS) < .001, info
    if mode == 'encode':
        (OUT / 'video_validation.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    print('VIDEO_OK', json.dumps(info), flush=True)
elif mode == 'finalize':
    s.camera = bpy.data.objects['04 | Animated camera']
    s.frame_set(1)
    engine(s)
    s.render.filepath = '//renders/Tower_Bridge_'
    text = bpy.data.texts.get('ПРОЧИТАЙТЕ | Управление проектом') or bpy.data.texts.new('ПРОЧИТАЙТЕ | Управление проектом')
    text.clear()
    text.write((OUT / 'НАЧНИТЕ ЗДЕСЬ.txt').read_text(encoding='utf-8'))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Tower_Bridge.blend'))
    print('FINALIZED: scene hash changed; render/encode after finalization.', flush=True)
else:
    raise ValueError(f'Unknown mode: {mode}')

