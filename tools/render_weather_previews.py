"""Render matching weather/population views on CPU without changing .blend files."""
import hashlib
import json
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'Tower_Bridge/extensions/weather'
records = []
for label, path in [('Clear_Busy', ROOT/'Tower_Bridge/Tower_Bridge.blend'),
                    ('Clear_Standard', OUT/'clear_standard/Tower_Bridge.blend'),
                    ('Overcast_Sparse', OUT/'overcast_sparse/Tower_Bridge.blend')]:
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    for marker in scene.timeline_markers:
        marker.camera = None
    scene.frame_set(1)
    scene.camera = bpy.data.objects['01 | Hero camera']
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(OUT/(label+'.png'))
    bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    records.append({'label': label, 'scene_sha256': before,
                    'image_sha256': hashlib.sha256((OUT/(label+'.png')).read_bytes()).hexdigest()})
(OUT/'previews_validation.json').write_text(json.dumps({'passed': True, 'size': [1920,1080],
    'renderer': 'Cycles CPU 16 samples; denoised', 'images': records}, indent=2), encoding='utf-8')
