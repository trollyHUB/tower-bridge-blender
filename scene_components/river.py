"""Layered river motion, small launch and vessel-local wakes without simulation caches."""
import math
from .scenario import CONFIG, END, FPS, reference_frame, boat_y

def build(g):
    bpy=g['bpy']; group=g['group'];box=g['box'];beam=g['beam'];empty=g['empty']
    boat=g['boat'];boat['actor_type']='sailboat';boat['length']=14.0;boat['height']=25.0
    for f in range(1,END+1,3):
        t=(f-1)/FPS
        boat.location=(0,boat_y(f),.045*math.sin(t*1.8))
        boat.rotation_euler=(.006*math.sin(t*1.5),.008*math.sin(t*1.8),0)
        boat.keyframe_insert('location',frame=f);boat.keyframe_insert('rotation_euler',frame=f)
    # Dense but inexpensive grid with two independent large wave fields.
    verts=[];faces=[];nx=100;ny=90
    for j in range(ny+1):
        for i in range(nx+1):verts.append((-109+218*i/nx,-85+170*j/ny,.9))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    mesh=bpy.data.meshes.new('Thames surface grid');mesh.from_pydata(verts,[],faces);mesh.materials.append(g['watermat'])
    ob=bpy.data.objects.new('Thames | layered animated waves',mesh);g['coll']('River | water and wakes').objects.link(ob)
    ob.shape_key_add(name='Basis')
    for k in range(2):
        key=ob.shape_key_add(name='Current wave '+str(k))
        for v in key.data:v.co.z += CONFIG['water']['amplitude']*math.sin(v.co.x*.45+v.co.y*.32+k*1.57)
        for f in range(1,END+1,6):
            key.value=.5+.5*math.sin((f-1)/FPS*1.3+k*1.57);key.keyframe_insert('value',frame=f)
    for p in mesh.polygons:p.use_smooth=True
    launch=empty('River launch | low clearance route','River | vessels',(16,52,0))
    launch['actor_type']='launch';launch['length']=8.;launch['height']=3.7
    group('River launch','River | vessels',launch)
    outline=[(-1.4,-4),(-1.7,1),(0,4),(1.7,1),(1.4,-4)]
    v=[(x*.7,y,.5) for x,y in outline]+[(x,y,1.8) for x,y in outline]
    g['meshpart'](v,[(0,4,3,2,1),(5,6,7,8,9)]+[(i,(i+1)%5,(i+1)%5+5,i+5) for i in range(5)],g['navy'])
    box((0,-1,2.4),(2.4,3.2,1.3),g['ivory']);box((0,-1,3.1),(2.8,3.5,.15),g['blue'])
    box((0,.65,2.65),(2.15,.08,.65),g['glass'])
    for side in [-1,1]:box((side*1.23,-1,2.65),(.08,2.7,.65),g['glass'])
    for f in range(1,END+1,3):
        t=(f-1)/FPS;launch.location=(16,52-104*(f-1)/(END-1),.04*math.sin(t*1.8+1))
        launch.rotation_euler=(.009*math.sin(t*1.8),.01*math.cos(t*1.8),math.pi)
        launch.keyframe_insert('location',frame=f);launch.keyframe_insert('rotation_euler',frame=f)
    foam=g['material']('River | restrained foam',(.45,.64,.61),rough=.4)
    for vessel in [boat,launch]:
        wake=empty(vessel.name+' | speed wake','River | water and wakes');wake.parent=vessel
        group(vessel.name+' wake','River | water and wakes',wake)
        length=14 if vessel==boat else 9
        for side in [-1,1]:
            for i in range(15):
                distance=i*length/15
                beam((side*(1.5+distance*.23),-5-distance,.93),(side*(1.5+(distance+.6)*.23),-5-distance-.6,.93),.065*(1-i/18),foam)
        for f in range(1,END+1,3):
            speed=abs(boat_y(min(END,f+3))-boat_y(max(1,f-3)))*FPS/6 if vessel==boat else 104/60
            wake.scale=(1,max(.03,min(1,speed/3)),1)
            wake.keyframe_insert('scale',frame=f)
        for side,col in [(-1,(1,.025,.01)),(1,(.03,1,.15))]:
            mat=g['material'](vessel.name+' navigation '+str(side),col,rough=.3)
            bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(*col,1);bs.inputs['Emission Strength'].default_value=3
            group(vessel.name+' navigation','River | vessels',vessel);g['sphere']((side*1.5,1,2.2),.12,mat)
    group('River completed','River | vessels')
