"""Evaluate the saved Blender scene, including every frame of moving actors."""
import json, math, hashlib
from .scenario import END, FPS, opening, reference_frame

def validate(scene, out):
    import bpy
    assert scene.frame_end == END and scene.render.fps == FPS
    control=bpy.data.objects['BRIDGE CONTROL | Opening degrees']
    records=[]
    for f in range(1,END+1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        angle=control['Opening degrees']
        assert abs(angle-opening(f))<.001, (f,angle)
        north=bpy.data.objects['North bascule hinge'].rotation_euler.y
        south=bpy.data.objects['South bascule hinge'].rotation_euler.y
        assert abs(north+south)<.0001
        if f in [1,192,336,432,624,720,864,1056,1104,1200,END]:
            records.append({'frame':f,'angle':angle})
    scene.frame_set(round(END/2));bpy.context.view_layer.update()
    moving=[o for o in bpy.data.objects if o.type=='MESH' and o.parent and 'bascule hinge' in o.parent.name]
    height=max((o.matrix_world@v.co).z for o in moving for v in o.data.vertices)
    assert height<43.1, ('upper walkway clearance',height)
    assert all(i.source!='FILE' or i.packed_file for i in bpy.data.images)
    report={'passed':True,'frames_checked':END,'hinge_samples':records,'raised_max_z':height}
    if any(o.get('actor_type')=='vehicle' for o in bpy.data.objects):
        from .traffic_validation import validate as traffic_validate
        report['traffic']=traffic_validate(scene)
    (out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('VALIDATION_OK',json.dumps(report),flush=True)
