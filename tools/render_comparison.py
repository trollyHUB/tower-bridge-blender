"""Render matched cameras for the saved v1 baseline and the completed scene."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/comparison'
OUT.mkdir(parents=True,exist_ok=True)
shots=[
    ('social',1200,(-174,-18,35),(-148,15,11),48),
    ('river',720,(35,-65,40),(0,-5,2),60),
    ('architecture',720,(-82,-75,65),(-39,0,43),62),
    ('evening',1440,(175,-235,145),(0,0,23),320),
]
for version,path in [('before',ROOT/'research/before_v1/Tower_Bridge.blend'),('after',ROOT/'Tower_Bridge/Tower_Bridge.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(path));scene=bpy.context.scene
    for marker in scene.timeline_markers:marker.camera=None
    scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32
    scene.render.resolution_x=1200;scene.render.resolution_y=675;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    data=bpy.data.cameras.new('Matched comparison');cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam)
    data.type='ORTHO';data.clip_end=3000
    for name,reference,location,target,scale in shots:
        scene.frame_set(round(reference*scene.frame_end/1440));scene.camera=cam
        cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
        scene.render.filepath=str(OUT/f'{version}_{name}.png');bpy.ops.render.render(write_still=True)
        print('COMPARISON_OK',version,name,flush=True)
