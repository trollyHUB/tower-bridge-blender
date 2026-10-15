"""Reproducible rendering, resumable frame caches, encoding and verification."""
import hashlib
import json
import sys
import time
import os
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scene_components.render_manifest import sha, make_identity, cache_directory, png_size, check_frames
from scene_components.settings import load_config, frame_count
OUT = Path(os.environ.get('TOWER_BRIDGE_OUTPUT', str(ROOT / 'Tower_Bridge')))
CONFIG = Path(os.environ.get('TOWER_BRIDGE_CONFIG', str(ROOT / 'config' / 'scene.json')))
cfg = load_config(CONFIG)
FPS = int(cfg['fps'])
COUNT = frame_count(cfg)
WIDTH, HEIGHT = int(cfg['render']['width']), int(cfg['render']['height'])
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['stills']
mode = args[0]
profile = 'preview' if mode in ('preview', 'preview_encode') else 'final'

def identity(profile='final'):
    data = make_identity(OUT / 'Tower_Bridge.blend', CONFIG, Path(__file__), profile, bpy.app.version_string)
    data['manifest_implementation_sha256'] = sha(ROOT / 'scene_components' / 'render_manifest.py')
    return data

def cache(profile):
    return cache_directory(ROOT / 'research' / 'render_runs', identity(profile))

def cycles_device(scene, requested):
    scene.cycles.device = 'CPU'
    if requested == 'cpu':
        return
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
                    return
            except Exception:
                continue
    except Exception:
        pass
    if requested == 'gpu':
        raise RuntimeError('render.device=gpu requires an available Cycles GPU')


def engine(scene, still=False):
    settings = cfg['render']
    device = settings.get('device', 'auto').lower()
    configured_engine = settings.get('engine', 'EEVEE').upper()
    if device not in ('auto', 'cpu', 'gpu'):
        raise ValueError('render.device must be auto, cpu or gpu')
    if configured_engine not in ('EEVEE', 'CYCLES'):
        raise ValueError('render.engine must be EEVEE or CYCLES')
    samples = int(settings.get('still_samples', settings.get('samples', 16)) if still else
                  settings.get('preview_samples', settings.get('samples', 16)) if profile == 'preview' else
                  settings.get('samples', 16))
    if samples < 1:
        raise ValueError('Render sample counts must be positive')
    use_cycles = still or configured_engine == 'CYCLES' or device == 'cpu'
    if not use_cycles:
        for name in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
            try:
                scene.render.engine = name
                break
            except (TypeError, ValueError):
                continue
        else:
            use_cycles = True
    if use_cycles:
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        cycles_device(scene, device)
    else:
        eevee = getattr(scene, 'eevee', None)
        if eevee is None:
            raise RuntimeError('Selected Eevee engine exposes no sample settings')
        # Prefer the render-specific setting when the version exposes both.
        if hasattr(eevee, 'taa_render_samples'):
            eevee.taa_render_samples = samples
        elif hasattr(eevee, 'taa_samples'):
            eevee.taa_samples = samples
        else:
            raise RuntimeError('Cannot apply requested Eevee render samples')
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = int(settings.get('preview_scale', 25)) if profile == 'preview' else 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.fps = FPS
    scene.render.fps_base = 1.0


def memory_usage():
    import platform
    if platform.system() == 'Windows':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        api = ctypes.WinDLL('psapi', use_last_error=True).GetProcessMemoryInfo
        api.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        api.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not api(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'peak_rss_bytes': counters.PeakWorkingSetSize, 'rss_bytes': counters.WorkingSetSize,
                'memory_source': 'GetProcessMemoryInfo'}
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {'peak_rss_bytes': peak if platform.system() == 'Darwin' else peak * 1024,
            'memory_source': 'getrusage'}

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
        if cfg['render'].get('device', 'auto').lower() != 'auto' or scene.render.engine != 'CYCLES' or scene.cycles.device != 'GPU':
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
    # Blender reapplies bound timeline cameras when rendering a still. Clear
    # bindings in this in-memory copy so the explicitly requested view wins.
    for marker in s.timeline_markers:
        marker.camera = None
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
        frames = sorted(set([1, max(1, COUNT // 4), max(1, COUNT // 2), COUNT]))
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
        measurement={'frame': frame, 'seconds': seconds}
        if mode=='benchmark':measurement.update(memory_usage())
        timings.append(measurement)
        if mode == 'benchmark' or frame % FPS == 0:
            print('FRAME_OK', frame, COUNT, round(seconds, 3), flush=True)
    if mode == 'benchmark':
        report = {'identity': identity(), 'timings': timings, 'engine': s.render.engine}
        try:
            report.update(memory_usage())
        except (ImportError, OSError) as error:
            report['memory_error'] = str(error)
        (OUT / 'benchmark.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
elif mode in ('encode', 'preview_encode', 'video_check'):
    target = OUT / ('Tower_Bridge_Preview.mp4' if profile == 'preview' else 'Tower_Bridge_Animation.mp4')
    signature = identity(profile)
    video_width, video_height = signature['size']
    if mode in ('encode', 'preview_encode'):
        directory = cache(profile)
        check_frames(directory, COUNT, signature['size'])
    else:
        report = json.loads((OUT / 'video_validation.json').read_text())
        assert report['identity'] == signature, 'Video belongs to an earlier scene/configuration'
        assert report['video_sha256'] == sha(target), 'Video hash mismatch'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = video_width, video_height
    s.render.resolution_percentage = 100
    s.render.fps = FPS
    s.render.fps_base = 1.0
    s.frame_start, s.frame_end = 1, COUNT
    s.render.use_sequencer = True
    s.view_settings.view_transform = 'Standard'
    seq = s.sequence_editor_create()
    collection = seq.strips if hasattr(seq, 'strips') else seq.sequences
    if mode in ('encode', 'preview_encode'):
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
        for frame in sorted(set(max(1, round(COUNT * fraction)) for fraction in (0, 1/6, 1/3, 1/2, 2/3, 5/6, 1))):
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
    assert info['frames'] == COUNT and info['size'] == [video_width, video_height], info
    assert abs(info['fps'] - FPS) < .001, info
    if mode in ('encode', 'preview_encode'):
        (OUT / ('preview_validation.json' if profile == 'preview' else 'video_validation.json')).write_text(json.dumps(info, indent=2), encoding='utf-8')
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

