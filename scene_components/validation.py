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
    if scene.get('City buildings'):
        from .environment_validation import validate as environment_validate
        report['environment']=environment_validate(scene)
    lamps=[o for o in scene.objects if o.type=='LIGHT' and o.name.startswith('Practical lantern')]
    if lamps:
        scene.frame_set(1)
        assert all(o.data.energy<.001 for o in lamps)
        scene.frame_set(END)
        assert all(o.data.energy>200 for o in lamps)
        report['practical_lights']={'count':len(lamps),'day_off_evening_on':True}
    snapshots=[]
    for f in [1,round(END/4),round(END/2),END]:
        scene.frame_set(f);bpy.context.view_layer.update()
        snapshots.append([(o.name,tuple(round(v,5) for row in o.matrix_world for v in row)) for o in sorted(scene.objects,key=lambda o:o.name)])
    report['deterministic_transform_sha256']=hashlib.sha256(json.dumps(snapshots).encode()).hexdigest()
    report['scene_sha256']=hashlib.sha256((out/'Tower_Bridge.blend').read_bytes()).hexdigest()
    (out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('VALIDATION_OK',json.dumps(report),flush=True)
