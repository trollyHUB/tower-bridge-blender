"""Decode every configured MP4 frame through Blender VSE at a small QA size.

This checks complete decoding and PNG integrity, not visual quality or whether
all rendered images portray the intended action. Run after Encode/VideoCheck.
"""
import json
import sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scene_components.settings import load_config, frame_count
from scene_components.render_manifest import sha, png_size, make_identity

cfg=load_config()
count=frame_count(cfg)
out=ROOT/'Tower_Bridge'
video=out/'Tower_Bridge_Animation.mp4'
scene_path=out/'Tower_Bridge.blend'
metadata=json.loads((out/'video_validation.json').read_text(encoding='utf-8'))
identity=make_identity(scene_path,ROOT/'config/scene.json',ROOT/'render_tower_bridge.py','final',bpy.app.version_string)
identity['manifest_implementation_sha256']=sha(ROOT/'scene_components/render_manifest.py')
assert metadata['identity']==identity, 'Stale video inputs'
video_sha=sha(video)
assert metadata['video_sha256']==video_sha, 'Video hash mismatch'
assert metadata['frames']==count and metadata['size']==[cfg['render']['width'],cfg['render']['height']]
assert abs(metadata['fps']-cfg['fps'])<.001

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
width=192
height=max(2,round(width*cfg['render']['height']/cfg['render']['width']/2)*2)
scene.render.resolution_x=width
scene.render.resolution_y=height
scene.render.resolution_percentage=100
scene.render.fps=cfg['fps']
scene.render.fps_base=1
scene.frame_start=1
scene.frame_end=count
scene.render.use_sequencer=True
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='Standard'
editor=scene.sequence_editor_create()
strips=editor.strips if hasattr(editor,'strips') else editor.sequences
strip=strips.new_movie('Full finished movie decode',str(video),channel=1,frame_start=1)
# VSE retains native movie pixel size; fit explicitly instead of center-cropping.
strip.transform.scale_x=width/cfg['render']['width']
strip.transform.scale_y=height/cfg['render']['height']
clip=bpy.data.movieclips.load(str(video),check_existing=False)
assert clip.frame_duration==count and list(clip.size)==metadata['size']
assert abs(clip.fps-cfg['fps'])<.001
frames=ROOT/'research/full_decode'/video_sha[:16]
frames.mkdir(parents=True,exist_ok=True)
decoded=0
for frame in range(1,count+1):
    scene.frame_set(frame)
    target=frames/f'frame_{frame:06d}.png'
    scene.render.filepath=str(target)
    bpy.ops.render.render(write_still=True)
    assert png_size(target)==[width,height], ('Invalid decoded PNG',frame)
    decoded+=1
    if frame%cfg['fps']==0:
        print('FULL_DECODE_PROGRESS',frame,count,flush=True)
# Fail if sources changed while decoding.
assert sha(video)==video_sha and sha(scene_path)==identity['scene_sha256']
report={'passed':True,'mode':'full_decode','decoded_count':decoded,'frames':count,
        'fps':clip.fps,'size':list(clip.size),'decode_size':[width,height],
        'scene_sha256':identity['scene_sha256'],'config_sha256':identity['config_sha256'],
        'video_sha256':video_sha,'identity':identity,'blender_version':bpy.app.version_string,
        'scope':'Every configured frame decoded by Blender VSE; PNG CRC and complete pixel streams checked. No claim of visual inspection.'}
(out/'full_video_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FULL_VIDEO_DECODE_OK',json.dumps(report),flush=True)
