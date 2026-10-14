"""Render stills, animation frames, and assemble the video with Blender's encoder."""
import bpy, sys, json, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Tower_Bridge'
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'stills'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Tower_Bridge.blend'))
s=bpy.context.scene

def gpu():
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    s.cycles.device='GPU'

def cycles(samples=64):
    s.render.engine='CYCLES';s.cycles.samples=samples;s.cycles.use_denoising=True;gpu()

def eevee():
    s.render.engine='CYCLES'
    # Set by actual supported engine enum, allowing version differences.
    for engine in ['BLENDER_EEVEE_NEXT','BLENDER_EEVEE']:
        try:s.render.engine=engine;break
        except TypeError:pass
    s.eevee.taa_render_samples=24
    s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG'

if mode=='stills':
    cycles(80)
    s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
    for name,frame,cam in [('Tower_Bridge_Open',360,'01 | Hero camera'),('Tower_Bridge_Closed',1,'01 | Hero camera'),('Tower_Bridge_Detail',360,'02 | Architectural detail')]:
        s.frame_set(frame);s.camera=bpy.data.objects[cam]
        s.render.filepath=str(OUT/'renders'/f'{name}.png');bpy.ops.render.render(write_still=True)
        print('STILL_OK',name,flush=True)
elif mode=='benchmark':
    eevee();s.camera=bpy.data.objects['04 | Animated camera']
    for frame in [1,360,361]:
        t=time.time();s.frame_set(frame);s.render.filepath=str(OUT/'renders'/f'eevee_{frame}.png');bpy.ops.render.render(write_still=True)
        print('FRAME_SECONDS',frame,time.time()-t,flush=True)
    print('IMAGE_ENUM',[(x.identifier,x.name) for x in s.render.image_settings.bl_rna.properties['file_format'].enum_items],flush=True)
    print('MEDIA_TYPE',hasattr(s.render.image_settings,'media_type'),flush=True)
elif mode=='animation':
    eevee();s.camera=bpy.data.objects['04 | Animated camera']
    frames=ROOT/'research'/'animation_frames';frames.mkdir(parents=True,exist_ok=True)
    args=sys.argv[sys.argv.index('--')+2:]
    start=int(args[0]) if args else 1;end=int(args[1]) if len(args)>1 else 720
    for frame in range(start,end+1):
        path=frames/f'{frame:04d}.png'
        if path.exists():continue
        s.frame_set(frame);s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        if frame%24==0:print('ANIMATION_PROGRESS',frame,720,flush=True)
elif mode=='encode':
    args=sys.argv[sys.argv.index('--')+2:]
    count=int(args[0]) if args else 720
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
    s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
    s.render.fps=24;s.frame_start=1;s.frame_end=count
    seq=s.sequence_editor_create()
    collection=seq.strips if hasattr(seq,'strips') else seq.sequences
    strip=collection.new_image('Tower Bridge animation',str(ROOT/'research'/'animation_frames'/'0001.png'),channel=1,frame_start=1)
    for f in range(2,count+1):strip.elements.append(f'{f:04d}.png')
    strip.frame_final_duration=count
    assert len(strip.elements)==count
    s.render.use_sequencer=True
    s.view_settings.view_transform='Standard'
    try:s.render.image_settings.file_format='FFMPEG'
    except TypeError:
        s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG'
    s.render.ffmpeg.format='MPEG4';s.render.ffmpeg.codec='H264';s.render.ffmpeg.constant_rate_factor='HIGH';s.render.ffmpeg.ffmpeg_preset='GOOD'
    target=OUT/'Tower_Bridge_Animation.mp4' if count==720 else ROOT/'research'/'encoding_test.mp4'
    s.render.filepath=str(target)
    bpy.ops.render.render(animation=True)
    clip=bpy.data.movieclips.load(str(target),check_existing=False)
    info={'frames':clip.frame_duration,'size':list(clip.size),'fps':clip.fps,'bytes':target.stat().st_size}
    assert clip.frame_duration==count,info
    assert list(clip.size)==[1280,720],info
    assert abs(clip.fps-24)<.001,info
    if count==720:(OUT/'video_validation.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print('VIDEO_OK',json.dumps(info),flush=True)
elif mode=='video_check':
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
    s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
    s.render.fps=24;s.render.use_sequencer=True;s.view_settings.view_transform='Standard'
    seq=s.sequence_editor_create();collection=seq.strips if hasattr(seq,'strips') else seq.sequences
    collection.new_movie('Decoded finished MP4',str(OUT/'Tower_Bridge_Animation.mp4'),channel=1,frame_start=1)
    s.render.image_settings.file_format='PNG'
    for frame in [1,360,720]:
        s.frame_set(frame);s.render.filepath=str(ROOT/'research'/f'video_decoded_{frame}.png')
        bpy.ops.render.render(write_still=True)
    print('DECODE_OK',flush=True)
elif mode=='validate':
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    ctrl=bpy.data.objects['BRIDGE CONTROL | Opening degrees']
    data=[]
    for frame in [1,120,204,288,360,456,540,624,720]:
        s.frame_set(frame);bpy.context.view_layer.update()
        row={'frame':frame,'control_degrees':ctrl['Opening degrees'],'north_degrees':bpy.data.objects['North bascule hinge'].rotation_euler.y*180/3.141592653589793,'south_degrees':bpy.data.objects['South bascule hinge'].rotation_euler.y*180/3.141592653589793,'boat_y':bpy.data.objects['Sailing boat | crossing route'].location.y}
        assert abs(row['north_degrees']+row['south_degrees'])<.001
        assert -0.001<=row['control_degrees']<=68.001
        if frame in [1,120,624,720]:assert abs(row['north_degrees'])<.001
        if frame in [288,360,456]:assert abs(row['south_degrees']-68)<.001
        data.append(row)
    assert len(bpy.data.images)==2 or all(i.source!='FILE' or i.packed_file for i in bpy.data.images)
    # Verify that raised deck geometry stays below the fixed high-level walkways.
    s.frame_set(360);bpy.context.view_layer.update()
    moving=[o for o in bpy.data.objects if o.type=='MESH' and o.parent and 'bascule hinge' in o.parent.name]
    raised_max_z=max((o.matrix_world@v.co).z for o in moving for v in o.data.vertices)
    assert raised_max_z<43.1,(raised_max_z,'Walkway collision')
    # Sample the actual geometry rather than oversized rotated bounding boxes.
    cam=bpy.data.objects['04 | Animated camera']
    for frame in [1,120,204,288,360,456,540,624,720]:
        s.frame_set(frame);bpy.context.view_layer.update()
        bounds=[]
        for ob in bpy.data.objects:
            if ob.type!='MESH' or ob.name=='Studio floor':continue
            step=max(1,len(ob.data.vertices)//300)
            bounds.extend(world_to_camera_view(s,cam,ob.matrix_world@ob.data.vertices[i].co) for i in range(0,len(ob.data.vertices),step))
        assert min(p.z for p in bounds)>0
        # One percent tolerance for the intentionally wide establishing composition.
        assert min(p.x for p in bounds)>-.01 and max(p.x for p in bounds)<1.01
        assert min(p.y for p in bounds)>-.01 and max(p.y for p in bounds)<1.01
    print('CLEARANCE_OK',raised_max_z,flush=True)
    (OUT/'validation.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print('VALIDATION_OK',json.dumps(data),flush=True)
elif mode=='finalize':
    s.camera=bpy.data.objects['04 | Animated camera'];s.frame_set(1)
    cycles(64)
    # GPU preferences live outside .blend; CPU is a portable default on reopening.
    s.cycles.device='CPU'
    s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
    s.render.filepath='//renders/Tower_Bridge_'
    rus=bpy.data.texts.get('ПРОЧИТАЙТЕ | Управление проектом') or bpy.data.texts.new('ПРОЧИТАЙТЕ | Управление проектом')
    rus.clear();rus.write((OUT/'НАЧНИТЕ ЗДЕСЬ.txt').read_text(encoding='utf-8'))
    # Avoid save-version clutter while retaining the original build script.
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Tower_Bridge.blend'))
    print('FINALIZED',flush=True)
