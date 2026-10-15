"""Build an isolated ten-second periodic daylight scene; --render explicitly enables Eevee rendering."""
import argparse,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def periodic(frame,period,harmonic=1,phase=0):return math.sin(2*math.pi*harmonic*(frame-1)/period+phase)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    import bpy
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=ROOT/'Tower_Bridge/Tower_Bridge.blend');p.add_argument('--output-dir',type=Path,default=ROOT/'Tower_Bridge/extensions/day_loop');p.add_argument('--render',action='store_true');p.add_argument('--encode-only',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.output_dir.mkdir(parents=True,exist_ok=True)
    original=sha(a.input);bpy.ops.wm.open_mainfile(filepath=str(a.input));s=bpy.context.scene;s.frame_set(1)
    # Freeze evaluated day-one state before removing story animation from every ID.
    for ob in bpy.data.objects:
        matrix=ob.matrix_basis.copy();ob.animation_data_clear();ob.matrix_basis=matrix
    for group in (bpy.data.materials,bpy.data.worlds,bpy.data.lights,bpy.data.cameras,bpy.data.shape_keys):
        for data in group:
            data.animation_data_clear()
            if getattr(data,'node_tree',None):data.node_tree.animation_data_clear()
    s.animation_data_clear();s.timeline_markers.clear();s.frame_start=1;s.frame_end=240;s.render.fps=24
    camera=next((o for o in bpy.data.objects if o.type=='CAMERA' and 'Water camera' in o.name),s.camera);s.camera=camera
    hidden=[]
    # Remove all nonperiodic story actors and their descendants from this derived composition.
    for ob in bpy.data.objects:
        if ob.get('actor_type') in ('vehicle','sailboat','launch') or 'wake born' in ob.name or 'bow foam' in ob.name:
            for item in [ob,*ob.children_recursive]:
                item.hide_render=True;item.hide_viewport=True;item.hide_set(True)
            hidden.append(ob.name)
    driven=[]
    def drive(owner,prop,index,base,amplitude,harmonic=1,phase=0):
        curve=owner.driver_add(prop,index) if index is not None else owner.driver_add(prop)
        curve.driver.expression=f'{base:.12g}+{amplitude:.12g}*sin(2*pi*{harmonic}*(frame-1)/240+{phase:.12g})';driven.append(curve.driver.expression)
    for keys in bpy.data.shape_keys:
        for i,key in enumerate(list(keys.key_blocks)[1:]):
            key.value=0;drive(key,'value',None,0,.65,1+i%3,i*.61)
    for ob in bpy.data.objects:
        if ob.get('actor_type')=='moored':
            drive(ob,'location',2,ob.location.z,.035,2);drive(ob,'rotation_euler',0,ob.rotation_euler.x,.008,1)
    assert driven,'Expected animated water shape keys in source'
    # All motion is integer-harmonic analytic sinusoids: endpoint values and first derivatives agree.
    seam=[]
    for h in (1,2,3):
        value_error=abs(periodic(1,240,h)-periodic(241,240,h));eps=.001
        derivative_error=abs((periodic(1+eps,240,h)-periodic(1-eps,240,h))-(periodic(241+eps,240,h)-periodic(241-eps,240,h)))/(2*eps)
        seam.append({'harmonic':h,'value_error':value_error,'derivative_error':derivative_error})
    def state(frame):
        s.frame_set(math.floor(frame), subframe=frame-math.floor(frame));bpy.context.view_layer.update()
        return [v for ob in s.objects if not ob.hide_render for row in ob.matrix_world for v in row]+[k.value for keys in bpy.data.shape_keys for k in keys.key_blocks]
    first=state(1);last=state(241);error=max(abs(x-y) for x,y in zip(first,last));assert error<1e-5,error
    epsilon=.01
    left_a=state(1-epsilon);left_b=state(1+epsilon);right_a=state(241-epsilon);right_b=state(241+epsilon)
    velocity_error=max(abs((b-a)-(d-c))/(2*epsilon) for a,b,c,d in zip(left_a,left_b,right_a,right_b));assert velocity_error<1e-4,velocity_error
    s.frame_set(1);s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
    if hasattr(s,'eevee'):s.eevee.taa_render_samples=16
    s.render.image_settings.file_format='PNG';s.render.filepath='//renders/Day_Loop_'
    bpy.context.preferences.filepaths.save_version=0
    target=a.output_dir/'Tower_Bridge_Day_Loop.blend';bpy.ops.wm.save_as_mainfile(filepath=str(target))
    report={'passed':True,'source_sha256':original,'derived_sha256':sha(target),'tool_sha256':sha(__file__),'frames':240,'fps':24,'size':[1920,1080],'camera':camera.name,'daylight_source_frame':1,'drivers':driven,'hidden_story_actors':hidden,'endpoint_state_max_error':error,'endpoint_velocity_max_error':velocity_error,'seam':seam,'motion':'Periodic water shape keys and moored skiff heave/roll; story traffic, passing vessels and transient wakes removed. All other day-one state held constant.'}
    if a.render or a.encode_only:
        frames=ROOT/'research/day_loop_frames'/original[:12];frames.mkdir(parents=True,exist_ok=True);s.render.image_settings.file_format='PNG';s.render.filepath=str(frames.resolve())+'/'
        if a.render and not a.encode_only:bpy.ops.render.render(animation=True)
        assert all((frames/f'{f:04d}.png').is_file() for f in range(1,241))
        def pixels(frame):
            image=bpy.data.images.load(str((frames/f'{frame:04d}.png').resolve()),check_existing=False);values=list(image.pixels)[::16];bpy.data.images.remove(image);return values
        def difference(x,y):return sum(abs(a-b) for a,b in zip(x,y))/len(x)
        start,next_frame,previous,end=map(pixels,(1,2,239,240));wrap=difference(end,start);internal=(difference(start,next_frame)+difference(previous,end))/2
        report['pixel_seam']={'wrap_mean_absolute_difference':wrap,'adjacent_mean_absolute_difference':internal,'ratio':wrap/max(internal,1e-12),'no_duplicate_terminal_frame':wrap>1e-10};assert wrap>1e-10 and wrap<max(3*internal,.001),report['pixel_seam']
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100;s.render.fps=24;s.frame_start=1;s.frame_end=240;s.view_settings.view_transform='Standard'
        strip=s.sequence_editor_create().strips.new_image('Periodic daylight frames',str((frames/'0001.png').resolve()),channel=1,frame_start=1)
        for f in range(2,241):strip.elements.append(f'{f:04d}.png')
        strip.frame_final_duration=240;s.render.use_sequencer=True;s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG';s.render.ffmpeg.format='MPEG4';s.render.ffmpeg.codec='H264';s.render.ffmpeg.gopsize=1;s.render.ffmpeg.constant_rate_factor='HIGH';video=a.output_dir/'Tower_Bridge_Day_Loop.mp4';s.render.filepath=str(video.resolve());bpy.ops.render.render(animation=True);report['video_sha256']=sha(video)
    assert sha(a.input)==original
    (a.output_dir/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if __name__=='__main__':main()

