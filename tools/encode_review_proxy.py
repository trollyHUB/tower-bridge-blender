"""Encode an explicitly labelled final-frame review proxy with Blender VSE."""
import argparse
import json
import sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scene_components.settings import load_config, frame_count
from scene_components.render_manifest import sha, make_identity, check_frames

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--proxy-cache',type=Path)
options=parser.parse_args(args)
cfg=load_config();count=frame_count(cfg)
expected=make_identity(ROOT/'Tower_Bridge/Tower_Bridge.blend',ROOT/'config/scene.json',ROOT/'render_tower_bridge.py','final',bpy.app.version_string)
expected['manifest_implementation_sha256']=sha(ROOT/'scene_components/render_manifest.py')
candidates=[options.proxy_cache] if options.proxy_cache else sorted((ROOT/'research/review_proxy').glob('*'))
valid=[]
for directory in candidates:
    path=directory/'manifest.json'
    if not path.is_file():continue
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('profile')=='review_proxy' and manifest.get('method')=='downsample_final' and manifest.get('source_identity')==expected:
        valid.append((directory,manifest))
assert len(valid)==1, 'Expected exactly one compatible review proxy; pass --proxy-cache'
directory,manifest=valid[0]
assert manifest['frames']==count and manifest['fps']==cfg['fps']
size=[cfg['render']['width']*cfg['render']['preview_scale']//100,cfg['render']['height']*cfg['render']['preview_scale']//100]
assert manifest['size']==size
check_frames(directory,count,size)
# Resolve source through its exact manifest identity, not its folder name.
sources=[path.parent for path in (ROOT/'research/render_runs').glob('*/manifest.json') if json.loads(path.read_text(encoding='utf-8'))==expected]
assert len(sources)==1, 'Missing or ambiguous final source cache'
for frame in range(1,count+1):
    name=f'{frame:04d}.png';record=manifest['images'][name]
    assert sha(directory/name)==record['proxy_sha256'], ('Changed proxy frame',frame)
    assert sha(sources[0]/name)==record['source_sha256'], ('Changed source frame',frame)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.resolution_x,scene.render.resolution_y=size
scene.render.resolution_percentage=100
scene.render.fps=cfg['fps'];scene.render.fps_base=1
scene.frame_start=1;scene.frame_end=count
scene.render.use_sequencer=True
scene.view_settings.view_transform='Standard'
editor=scene.sequence_editor_create()
strips=editor.strips if hasattr(editor,'strips') else editor.sequences
strip=strips.new_image('Review proxy from final frames',str(directory/'0001.png'),channel=1,frame_start=1)
for frame in range(2,count+1):strip.elements.append(f'{frame:04d}.png')
strip.frame_final_duration=count
try:scene.render.image_settings.file_format='FFMPEG'
except TypeError:
    scene.render.image_settings.media_type='VIDEO'
    scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='HIGH';scene.render.ffmpeg.ffmpeg_preset='GOOD'
target=ROOT/'Tower_Bridge/Tower_Bridge_ReviewProxy.mp4'
scene.render.filepath=str(target)
bpy.ops.render.render(animation=True)
clip=bpy.data.movieclips.load(str(target),check_existing=False)
assert clip.frame_duration==count and list(clip.size)==size and abs(clip.fps-cfg['fps'])<.001
report={'passed':True,'profile':'review_proxy','method':'downsample_final','source_identity':expected,
        'frames':clip.frame_duration,'fps':clip.fps,'size':list(clip.size),
        'video_sha256':sha(target),'bytes':target.stat().st_size,
        'proxy_manifest_sha256':sha(directory/'manifest.json'),
        'scope':'All proxy and source frame hashes verified; encoded from downsampled final frames. No separate low-sample rendering claim.'}
(ROOT/'Tower_Bridge/review_proxy_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('REVIEW_PROXY_VIDEO_OK',json.dumps(report),flush=True)
