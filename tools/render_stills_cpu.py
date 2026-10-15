"""Render the six release views on CPU, leaving the configured main scene intact."""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'Tower_Bridge'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Tower_Bridge.blend'))
s = bpy.context.scene
count = s.frame_end
for marker in s.timeline_markers:
    marker.camera = None
s.render.engine = 'CYCLES'
s.cycles.device = 'CPU'
s.cycles.samples = 32
s.cycles.use_denoising = True
s.render.resolution_percentage = 100
shots = [('Open',count//2,'01 | Hero camera'),('Closed',1,'01 | Hero camera'),
         ('City',count//4,'05 | City camera'),('Water',count//2,'06 | Water camera'),
         ('Evening',count,'07 | Evening camera'),('Detail',count//2,'02 | Architectural detail')]
for name,frame,camera in shots:
    s.frame_set(frame)
    s.camera = bpy.data.objects[camera]
    s.render.filepath = str(OUT/'renders'/f'Tower_Bridge_{name}.png')
    bpy.ops.render.render(write_still=True)
    print('CPU_STILL_OK',name,flush=True)
