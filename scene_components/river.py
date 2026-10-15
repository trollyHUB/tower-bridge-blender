"""Analytic water, sampled buoyancy and historical world-space vessel wakes."""
import math
from .scenario import CONFIG, END, FPS, boat_y
from .wind import wind_time
from .water_math import surface_height, vessel_pose, wave_modes, wake_state


def build(g):
    bpy=g['bpy']; group=g['group']; box=g['box']; beam=g['beam']; empty=g['empty']
    level=CONFIG['water']['level']; collection='River | water and wakes'
    boat=g['boat']; boat['actor_type']='sailboat'; boat['length']=14.; boat['height']=25.
    boat.animation_data_clear()
    verts=[]; faces=[]; nx=218; ny=170
    for j in range(ny+1):
        for i in range(nx+1):verts.append((-109+i,-85+j,level))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i; faces.append((a,a+1,a+nx+2,a+nx+1))
    mesh=bpy.data.meshes.new('Thames surface grid'); mesh.from_pydata(verts,[],faces); mesh.materials.append(g['watermat'])
    ob=bpy.data.objects.new('Thames | analytic wind surface',mesh); g['coll'](collection).objects.link(ob)
    ob['surface_contract']='water_math.surface_height; integer frames; grid spacing 1m'
    ob.shape_key_add(name='Basis',from_mix=False)
    # sin(s-wt) = sin(s) cos(wt) - cos(s) sin(wt), exact at mesh vertices.
    for index,(a,kx,ky,w,p) in enumerate(wave_modes(CONFIG)):
        for trig,label in [(math.sin,'sin'),(math.cos,'cos')]:
            key=ob.shape_key_add(name=f'Wind mode {index} {label}',from_mix=False); key.slider_min=-1; key.slider_max=1
            for v in key.data:v.co.z+=a*trig(kx*v.co.x+ky*v.co.y+p)
            for f in range(1,END+1):
                t=(f-1)/FPS; key.value=math.cos(w*wind_time(t)) if label=='sin' else -math.sin(w*wind_time(t))
                key.keyframe_insert('value',frame=f)
    for p in mesh.polygons:p.use_smooth=True
    launch=empty('River launch | low clearance route','River | vessels',(16,52,0))
    launch['actor_type']='launch'; launch['length']=8.; launch['height']=3.7
    group('River launch','River | vessels',launch)
    outline=[(-1.4,-4),(-1.7,1),(0,4),(1.7,1),(1.4,-4)]
    v=[(x*.7,y,.5) for x,y in outline]+[(x,y,1.8) for x,y in outline]
    g['meshpart'](v,[(0,4,3,2,1),(5,6,7,8,9)]+[(i,(i+1)%5,(i+1)%5+5,i+5) for i in range(5)],g['navy'])
    box((0,-1,2.4),(2.4,3.2,1.3),g['ivory']); box((0,-1,3.1),(2.8,3.5,.15),g['blue'])
    box((0,.65,2.65),(2.15,.08,.65),g['glass'])
    for side in [-1,1]:box((side*1.23,-1,2.65),(.08,2.7,.65),g['glass'])
    def route(vessel,f):
        return (0,boat_y(f),0.) if vessel==boat else (16,52-104*(f-1)/(END-1),math.pi)
    def speed_at(vessel,f):
        lo=max(1,f-1); hi=min(END,f+1)
        return abs(route(vessel,hi)[1]-route(vessel,lo)[1])*FPS/(hi-lo)
    for vessel in [boat,launch]:
        vessel['buoyancy_surface']='water_math.surface_height'; vessel['nominal_waterline']=.9
        for f in range(1,END+1):
            x,y,heading=route(vessel,f); z,rotation=vessel_pose(x,y,(f-1)/FPS,heading,CONFIG)
            vessel.location=(x,y,z); vessel.rotation_euler=rotation
            vessel.keyframe_insert('location',frame=f); vessel.keyframe_insert('rotation_euler',frame=f)
        for side,col in [(-1,(1,.025,.01)),(1,(.03,1,.15))]:
            mat=g['material'](vessel.name+' navigation '+str(side),col,rough=.3)
            bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Emission Color'].default_value=(*col,1); bs.inputs['Emission Strength'].default_value=3
            group(vessel.name+' navigation','River | vessels',vessel); g['sphere']((side*1.5,1,2.2),.12,mat)
        foam=g['material'](vessel.name+' bow foam',(.45,.64,.61),rough=.4)
        bow=empty(vessel.name+' | bow foam',collection); bow.parent=vessel
        group(vessel.name+' bow foam',collection,bow)
        nose=6 if vessel==boat else 3.6
        for side in [-1,1]:beam((0,nose,.94),(side*1.6,nose-1.8,.94),.11,foam)
        for f in range(1,END+1):
            amount=min(1.,speed_at(vessel,f)/2.5); bow.scale=(amount,amount,1)
            bow.keyframe_insert('scale',frame=f)
        # Each patch is born at a historical world position and then drifts independently.
        for birth in range(1,END+1,max(1,round(FPS*.7))):
            speed=speed_at(vessel,birth)
            if speed<.05:continue
            x,y,heading=route(vessel,birth); direction=math.cos(heading); stern=5.8 if vessel==boat else 3.8
            for side in [-1,1]:
                patch=empty(f'{vessel.name} | wake born {birth} side {side}',collection)
                patch['wake_birth_frame']=birth; patch['wake_speed']=speed; patch['world_space_wake']=True
                mat=g['material'](patch.name+' foam',(.45,.64,.61),rough=.4)
                mat.surface_render_method='DITHERED'
                bs=mat.node_tree.nodes.get('Principled BSDF')
                group(patch.name,collection,patch)
                beam((0,0,0),(side*.8,-direction*.9,0),.09,mat)
                patch.scale=(0,0,0); patch.keyframe_insert('scale',frame=max(1,birth-1))
                for f in range(birth,min(END,birth+math.ceil(FPS*CONFIG['water'].get('wake_lifetime',4.)))+1):
                    age=(f-birth)/FPS; dx,dy,fade=wake_state(age,speed,CONFIG)
                    px=x+side*(1.3+age*.65)+dx; py=y-direction*(stern+age*.25)+dy
                    patch.location=(px,py,surface_height(px,py,(f-1)/FPS,CONFIG)+.035)
                    patch.scale=(fade*(1+age*.5),fade*(1+age*.5),max(.001,fade))
                    patch.keyframe_insert('location',frame=f); patch.keyframe_insert('scale',frame=f)
                    bs.inputs['Alpha'].default_value=fade; bs.inputs['Alpha'].keyframe_insert('default_value',frame=f)
    # Mooring furniture connects the existing bank docks to driven piles.
    group('Dock | mooring ropes and piles',collection)
    rope=g['material']('Dock | hemp mooring rope',(.32,.23,.12),rough=.9)
    wood=g['material']('River | mooring oak',(.22,.12,.055),rough=.8)
    for side in [-1,1]:
        for y in [31,39]:
            x=side*101.8
            g['cyl']((x,y,1.25),.23,3.6,wood,n=10)
            points=[(side*105,y,2.5),(side*103.4,y,1.8),(x,y,2.7)]
            for a,b in zip(points,points[1:]):beam(a,b,.065,rope)
    for side in [-1,1]:
        skiff=empty('Dock | moored rowing skiff '+str(side),'River | vessels')
        skiff['actor_type']='moored'; skiff['nominal_waterline']=.9
        group(skiff.name,'River | vessels',skiff)
        outline=[(-.8,-2.8),(-1,1.5),(0,3),(1,1.5),(.8,-2.8)]
        vertices=[(x,y,z) for z in [.55,1.25] for x,y in outline]
        g['meshpart'](vertices,[(0,4,3,2,1)]+[(i,(i+1)%5,(i+1)%5+5,i+5) for i in range(5)],wood)
        for yy in [-1.5,.5]:box((0,yy,1.15),(1.7,.4,.15),wood)
        for f in range(1,END+1):
            x=side*96; z,rotation=vessel_pose(x,35,(f-1)/FPS,0,CONFIG)
            skiff.location=(x,35,z); skiff.rotation_euler=rotation
            skiff.keyframe_insert('location',frame=f); skiff.keyframe_insert('rotation_euler',frame=f)
        group('Dock | skiff mooring lines '+str(side),collection)
        for yy in [-2,2]:
            points=[(side*96,35+yy,1.2),(side*97.5,35+yy,1.3),(side*99,35+yy,2.7)]
            for a,b in zip(points,points[1:]):beam(a,b,.055,rope)
    group('River completed','River | vessels')
