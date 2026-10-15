"""Original editable Tower Bridge study. Run with Blender 5.2 --background --python.
All geometry and materials are generated locally; no downloaded mesh is included.
"""
import bpy, math, json, random, sys, time
from pathlib import Path
from mathutils import Vector
from math import sin, cos, pi

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scene_components.scenario import CONFIG, END, FPS, opening, boat_y, frame, PHASES, linear_keys
OUT=ROOT/'Tower_Bridge'
OUT.mkdir(exist_ok=True)
(OUT/'renders').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
random.seed(CONFIG['seed'])
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=CONFIG['render']['width']
scene.render.resolution_y=CONFIG['render']['height']
scene.render.resolution_percentage=100
scene.render.fps=FPS
scene.frame_start=1
scene.frame_end=END
scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('Studio daylight')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.49,0.65,0.82,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.35
scene.view_settings.view_transform='AgX'
try: scene.view_settings.look='AgX - Medium High Contrast'
except: pass

def material(name,color,metal=0,rough=.5):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal
    bs.inputs['Roughness'].default_value=rough
    return m

stone=material('Portland limestone | subtle masonry',(.54,.49,.39),0,.76)
nt=stone.node_tree; bs=nt.nodes.get('Principled BSDF')
tex=nt.nodes.new('ShaderNodeTexCoord')
mapping=nt.nodes.new('ShaderNodeVectorMath'); mapping.operation='SCALE'; mapping.inputs[3].default_value=1
nt.links.new(tex.outputs['Object'],mapping.inputs[0])
brick=nt.nodes.new('ShaderNodeTexBrick')
brick.inputs['Color1'].default_value=(.56,.52,.43,1)
brick.inputs['Color2'].default_value=(.42,.39,.33,1)
brick.inputs['Mortar'].default_value=(.32,.30,.25,1)
brick.inputs['Scale'].default_value=1.1
brick.inputs['Mortar Size'].default_value=.011
brick.inputs['Mortar Smooth'].default_value=.015
brick.inputs['Brick Width'].default_value=1.9
brick.inputs['Row Height'].default_value=.65
# World-oriented masonry: project the long facade horizontally and keep Z vertical.
sep=nt.nodes.new('ShaderNodeSeparateXYZ'); comb=nt.nodes.new('ShaderNodeCombineXYZ')
nt.links.new(tex.outputs['Object'],sep.inputs[0])
add=nt.nodes.new('ShaderNodeMath'); add.operation='ADD'
nt.links.new(sep.outputs['X'],add.inputs[0]); nt.links.new(sep.outputs['Y'],add.inputs[1])
nt.links.new(add.outputs[0],comb.inputs['X']); nt.links.new(sep.outputs['Z'],comb.inputs['Y'])
nt.links.new(comb.outputs[0],brick.inputs['Vector'])
nt.links.new(brick.outputs['Color'],bs.inputs['Base Color'])
noise=nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=7; noise.inputs['Detail'].default_value=2
nt.links.new(tex.outputs['Object'],noise.inputs['Vector'])
bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.20; bump.inputs['Distance'].default_value=.08
nt.links.new(brick.outputs['Fac'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
trim=material('Pale carved limestone',(.72,.68,.56),0,.64)
foundation=material('Granite foundations',(.30,.33,.32),0,.8)
blue=material('Tower Bridge blue enamel',(.035,.29,.43),.38,.29)
lightblue=material('Light blue steel edges',(.14,.51,.65),.30,.3)
ivory=material('Ivory painted steel',(.80,.84,.79),.25,.32)
slate=material('Slate roofs',(.065,.10,.13),.2,.48)
glass=material('Smoky blue glazing',(.038,.095,.12),.52,.2)
dark=material('Deep window recesses',(.018,.031,.037),0,.9)
gold=material('Brass and gilded finials',(.53,.33,.09),.72,.26)
asphalt=material('Fine asphalt',(.055,.066,.075),0,.91)
red=material('London bus red',(.57,.018,.025),.25,.32)
rubber=material('Tyres',(.012,.016,.019),0,.8)
white=material('Road marking and sailcloth',(.85,.85,.76),0,.65)
navy=material('Midnight blue display plinth',(.012,.034,.054),.35,.36)
groundmat=material('Studio floor',(.12,.18,.22),0,.8)
lampmat=material('Warm lamp glass',(.95,.67,.27),.1,.24)
lampmat.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(1,.65,.24,1)
lampmat.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=2
watermat=material('Thames | animated procedural water',(.025,.16,.18),.45,.22)
wn=watermat.node_tree; wb=wn.nodes.get('Principled BSDF')
wb.inputs['IOR'].default_value=1.333
tc=wn.nodes.new('ShaderNodeTexCoord'); mp=wn.nodes.new('ShaderNodeMapping')
wn.links.new(tc.outputs['Object'],mp.inputs['Vector'])
mp.inputs['Scale'].default_value=(.42,1.6,1)
mp.inputs['Location'].default_value=(0,0,0); mp.inputs['Location'].keyframe_insert('default_value',frame=1)
mp.inputs['Location'].default_value=(0,8,0); mp.inputs['Location'].keyframe_insert('default_value',frame=END)
noise=wn.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=1.8; noise.inputs['Detail'].default_value=3; noise.inputs['Roughness'].default_value=.65
wn.links.new(mp.outputs['Vector'],noise.inputs['Vector'])
bump=wn.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.26; bump.inputs['Distance'].default_value=.25
wn.links.new(noise.outputs['Fac'],bump.inputs['Height']); wn.links.new(bump.outputs['Normal'],wb.inputs['Normal'])

collections={}
def coll(name):
    if name not in collections:
        c=bpy.data.collections.new(name); scene.collection.children.link(c); collections[name]=c
    return collections[name]

GROUP=''; COLLECTION=''; PARENT=None
buckets={}
def group(name,collection,parent=None):
    global GROUP,COLLECTION,PARENT
    GROUP,COLLECTION,PARENT=name,collection,parent

def meshpart(verts,faces,mat,smooth=False):
    key=(GROUP,COLLECTION,PARENT,mat.name)
    if key not in buckets: buckets[key]=[[],[],[],mat]
    v,f,s,m=buckets[key]; n=len(v); v.extend(verts); f.extend([tuple(i+n for i in face) for face in faces]); s.extend([smooth]*len(faces))

def box(c,d,mat,angle=0):
    x,y,z=c; a,b,h=(k/2 for k in d)
    v=[]
    for u,w,t in [(-a,-b,-h),(a,-b,-h),(a,b,-h),(-a,b,-h),(-a,-b,h),(a,-b,h),(a,b,h),(-a,b,h)]:
        v.append((x+u*cos(angle)-w*sin(angle),y+u*sin(angle)+w*cos(angle),z+t))
    meshpart(v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def beam(a,b,width,mat,depth=None):
    a,b=Vector(a),Vector(b); direction=b-a
    if direction.length<.00001:return
    q=direction.to_track_quat('Z','Y'); c=(a+b)/2; w=width/2; d=(depth or width)/2; h=direction.length/2
    verts=[tuple(c+q@Vector(p)) for p in [(-w,-d,-h),(w,-d,-h),(w,d,-h),(-w,d,-h),(-w,-d,h),(w,-d,h),(w,d,h),(-w,d,h)]]
    meshpart(verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def cyl(c,r,depth,mat,n=16,r2=None,axis=(0,0,1)):
    q=Vector(axis).to_track_quat('Z','Y'); center=Vector(c)
    r2=r if r2 is None else r2
    verts=[tuple(center+q@Vector((rr*cos(2*pi*i/n),rr*sin(2*pi*i/n),z))) for rr,z in [(r,-depth/2),(r2,depth/2)] for i in range(n)]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    meshpart(verts,faces,mat,False)

def sphere(c,r,mat):
    verts=[]; n=12; rows=6
    for j in range(rows+1):
        phi=pi*j/rows
        for i in range(n):verts.append((c[0]+r*sin(phi)*cos(2*pi*i/n),c[1]+r*sin(phi)*sin(2*pi*i/n),c[2]+r*cos(phi)))
    faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(rows) for i in range(n)]
    meshpart(verts,faces,mat,True)

def polyline(points,r,mat):
    for a,b in zip(points,points[1:]):beam(a,b,r,mat)

def ellipse_slab(rx,ry,z,h,mat,n=192):
    verts=[(rx*cos(2*pi*i/n),ry*sin(2*pi*i/n),zz) for zz in [z-h/2,z+h/2] for i in range(n)]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    meshpart(verts,faces,mat)

def ellipse_ring(rx,ry,width,z,h,mat,n=192):
    verts=[(a*cos(2*pi*i/n),b*sin(2*pi*i/n),zz) for zz in [z-h/2,z+h/2] for a,b in [(rx,ry),(rx-width,ry-width)] for i in range(n)]
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend([(i,j,j+2*n,i+2*n),(i+n,i+3*n,j+3*n,j+n),(i+2*n,j+2*n,j+3*n,i+3*n),(i,i+n,j+n,j)])
    meshpart(verts,faces,mat)

def hip_roof(cx,cy,z,w,d,h,mat):
    verts=[(cx+u,cy+v,z) for u,v in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]
    verts += [(cx+u,cy+v,z+h) for u,v in [(-.35,-d*.18),(.35,-d*.18),(.35,d*.18),(-.35,d*.18)]]
    meshpart(verts,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat)
    for i in range(4):beam(verts[i],verts[i+4],.13,gold)
    for k in range(1,15):
        t=k/15; ww=w*(1-t)+.7*t; dd=d*(1-t)+d*.36*t
        for a,b in [((-ww/2,-dd/2),(ww/2,-dd/2)),((ww/2,-dd/2),(ww/2,dd/2)),((ww/2,dd/2),(-ww/2,dd/2)),((-ww/2,dd/2),(-ww/2,-dd/2))]:
            beam((cx+a[0],cy+a[1],z+h*t),(cx+b[0],cy+b[1],z+h*t),.055,slate)

def empty(name,collection,loc=(0,0,0)):
    ob=bpy.data.objects.new(name,None); coll(collection).objects.link(ob); ob.location=loc; ob.empty_display_type='PLAIN_AXES'; ob.empty_display_size=3
    return ob

def facade_point(origin,u,z,face,offset=0):
    # Local U runs along the facade; offset is outwards.
    x,y,base=origin
    if face=='front':return (x+u,y-offset,base+z)
    if face=='back':return (x-u,y+offset,base+z)
    if face=='left':return (x-offset,y-u,base+z)
    return (x+offset,y+u,base+z)

def window(origin,w,h,face):
    p=lambda u,z,o=0:facade_point(origin,u,z,face,o)
    r=w/2; spring=h-r
    outline=[(-r,0),(r,0),(r,spring)]+[(r*cos(pi*i/12),spring+r*sin(pi*i/12)) for i in range(1,13)]
    meshpart([p(u,z,.055) for u,z in outline],[tuple(range(len(outline)))],dark)
    # Glazing is inset visually behind the carved moulding.
    glazing=[p(u*.80,z*.91+.13,.08) for u,z in outline]
    meshpart(glazing,[tuple(range(len(glazing)))],glass)
    beam(p(-r,-.13,.22),p(r,-.13,.22),.24,trim,.43)
    beam(p(-r,0,.2),p(-r,spring,.2),.18,trim)
    beam(p(r,0,.2),p(r,spring,.2),.18,trim)
    arc=[p(r*cos(pi*i/16),spring+r*sin(pi*i/16),.2) for i in range(17)]
    polyline(arc,.18,trim)
    beam(p(0,0,.23),p(0,h-.09,.23),.09,trim)
    for z in [spring*.37,spring*.75]:beam(p(-r+.08,z,.22),p(r-.08,z,.22),.08,trim)

def arch_x(cx,r,zspring,thick,depth):
    # voussoir ring through the roadway, facing along X
    for i in range(20):
        a=i*pi/20+.005; b=(i+1)*pi/20-.005
        v=[(xx,rr*cos(t),zspring+rr*sin(t)) for xx in [cx-depth/2,cx+depth/2] for rr,t in [(r,a),(r,b),(r+thick,b),(r+thick,a)]]
        meshpart(v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],trim)

# Foundation and water ---------------------------------------------------------
if CONFIG['features'].get('city'):
    group('London display plinth','01 | Diorama')
    box((0,0,-4.2),(438,180,5),navy)
    box((0,0,-1.7),(437,179,.2),gold)
    box((0,0,-1.1),(434,176,1),foundation)
    for yy in [-87,87]:box((0,yy,-.2),(434,1.2,.7),trim)
else:
    group('Display base','01 | Diorama')
    ellipse_slab(145,69,-4.2,5.0,navy)
    ellipse_ring(145.2,69.2,.35,-1.78,.18,gold)
    ellipse_slab(142,66,-1.2,.8,foundation)
    ellipse_slab(138,62,.25,1.3,watermat)
    ellipse_ring(143,67,5,1.4,2.1,stone)
    ellipse_ring(143.6,67.6,5.5,2.5,.35,trim)
    for i in range(168):
        a=2*pi*i/168
        beam((138.3*cos(a),62.3*sin(a),2.69),(143.3*cos(a),67.3*sin(a),2.69),.05,foundation)
    
    # Small geometrical water ripples, below the bump-mapped surface highlights.
    group('River surface ripples','01 | Diorama')
    for i in range(85):
        x=random.uniform(-115,115); y=random.uniform(-53,53)
        if x*x/132**2+y*y/58**2>.87:continue
        points=[(x+j*.8,y+.2*sin(j*.7+i),.91+.015*sin(j)) for j in range(5)]
        polyline(points,.026,lightblue)
    
for sign in [-1,1]:
    group(('North' if sign<0 else 'South')+' approach island','02 | Approaches')
    box((sign*116,0,4.9),(34,30,9.2),stone)
    box((sign*116,0,9.7),(35,31,.7),trim)
    for xx in [sign*102,sign*128]:
        for yy in [-12,12]:
            cyl((xx,yy,12),2.0,5,stone,8)
            cyl((xx,yy,14.7),2.35,.55,trim,8)
            cyl((xx,yy,16.6),2.3,3.2,slate,8,r2=.12)
            sphere((xx,yy,18.3),.26,gold)

# Two towers -----------------------------------------------------------------
for tx,label in [(-39,'North'),(39,'South')]:
    C='03 | '+label+' tower'
    group(label+' pier',C)
    # Rounded rectangular pier outline with pointed cutwaters.
    outline=[(-10,-12),(-8,-16),(0,-18),(8,-16),(10,-12),(10,12),(8,16),(0,18),(-8,16),(-10,12)]
    verts=[(tx+x,y,z) for z in [-.7,6] for x,y in outline]
    faces=[tuple(range(9,-1,-1)),tuple(range(10,20))]+[(i,(i+1)%10,(i+1)%10+10,i+10) for i in range(10)]
    meshpart(verts,faces,foundation)
    for z in [2,5.6,6.25]:
        for i in range(10):beam((tx+outline[i][0],outline[i][1],z),(tx+outline[(i+1)%10][0],outline[(i+1)%10][1],z),.35,trim)
    group(label+' tower masonry',C)
    # Actual clear tunnel: there is no cube filling the road opening.
    for y in [-9.1,9.1]:box((tx,y,15),(17,5.2,18),stone)
    box((tx,0,37.0),(17,23.4,26),stone)
    # Curved spandrels between the semicircular road arch and upper storeys.
    for side in [-1,1]:
        for i in range(16):
            y0=6.5*i/16; y1=6.5*(i+1)/16
            z0=17+math.sqrt(max(0,6.5**2-y0*y0)); z1=17+math.sqrt(max(0,6.5**2-y1*y1))
            v=[(xx,side*yy,zz) for xx in [tx-8.5,tx+8.5] for yy,zz in [(y0,z0),(y1,z1),(y1,24.05),(y0,24.05)]]
            meshpart(v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],stone)
    group(label+' arch stones',C)
    for xx in [tx-8.65,tx+8.65]:
        arch_x(xx,6.5,17,.85,.65)
        for yy in [-6.95,6.95]:
            box((xx,yy,13.5),(.7,.9,7),trim)
            for z in [10.5,11.7,12.9,14.1,15.3,16.5]:box((xx,yy,z),(.77,1,.10),foundation)
    group(label+' cornices',C)
    for z,w,d,h in [(7.1,18,24.4,.8),(24.4,18.1,24.4,.65),(26.1,17.9,24.1,.35),(33.9,17.6,24,.45),(41.8,18.1,24.5,.65),(49.8,18.3,24.7,.7),(51,19,25.2,.8)]:
        # Lower plinth does not block the tunnel.
        if z<10:
            for yy in [-9.25,9.25]:box((tx,yy,z),(w,5.3,h),trim)
        else:box((tx,0,z),(w,d,h),trim)
    group(label+' facade windows',C)
    for face,orig in [('front',(tx,-11.73,0)),('back',(tx,11.73,0))]:
        for zz,hh in [(13,4.8),(27.1,4.5),(35.2,4.8),(43,5.3)]:
            for dx in [-5.5,-2.75,0,2.75,5.5]:window((orig[0]+dx,orig[1],zz),1.5,hh,face)
    for face,xx in [('left',tx-8.54),('right',tx+8.54)]:
        for zz,hh in [(27.1,4.5),(35.2,4.8),(43,5.3)]:
            for yy in [-6.8,-3.4,0,3.4,6.8]:window((xx,yy,zz),1.6,hh,face)
    group(label+' corner turrets',C)
    for dx in [-7.5,7.5]:
        for yy in [-10.6,10.6]:
            x=tx+dx
            cyl((x,yy,38),1.85,28,stone,8)
            for z in [25,33.8,41.8,50.2,52.4]:cyl((x,yy,z),2.03,.5,trim,8)
            cyl((x,yy,54.2),1.76,3.1,stone,8)
            cyl((x,yy,55.8),2.05,.5,trim,8)
            cyl((x,yy,59.2),2.02,6.3,slate,8,r2=.15)
            cyl((x,yy,62.8),.1,1.2,gold,8)
            sphere((x,yy,63.5),.23,gold)
            for z in [29,37,45,52.7]:window((x,yy+(-1.76 if yy<0 else 1.76),z),.6,1.7,'front' if yy<0 else 'back')
    group(label+' central roof and gables',C)
    hip_roof(tx,0,51.5,14.4,18.9,9.3,slate)
    # Ornamental peaked gables on the wide river facades.
    for sign in [-1,1]:
        y=sign*11.9
        for dx in [-3.9,3.9]:
            meshpart([(tx+dx-1.8,y,50.9),(tx+dx+1.8,y,50.9),(tx+dx,y,56.3)],[(0,1,2)],stone)
            beam((tx+dx-1.95,y,50.8),(tx+dx,y,56.6),.25,trim)
            beam((tx+dx+1.95,y,50.8),(tx+dx,y,56.6),.25,trim)
            window((tx+dx,y,51.5),1.1,2.5,'front' if sign<0 else 'back')
            sphere((tx+dx,y,56.8),.2,gold)
    beam((tx,0,60.8),(tx,0,67.1),.12,gold)
    sphere((tx,0,67.2),.25,gold)
    flag=empty(label+' wind flag','Environment | flags',(tx,0,65.6))
    group(label+' flag','Environment | flags')
    # Union flag represented as original simple geometry, not an external image.
    box((tx+1.4,0,65.6),(2.8,.05,1.5),blue)
    box((tx+1.4,-.04,65.6),(2.8,.035,.27),white)
    box((tx+1.4,-.04,65.6),(.38,.035,1.5),white)
    beam((tx,.0,64.85),(tx+2.8,0,66.35),.19,white)
    beam((tx,0,66.35),(tx+2.8,0,64.85),.19,white)
    box((tx+1.4,-.10,65.6),(2.8,.035,.13),red)
    box((tx+1.4,-.10,65.6),(.18,.035,1.5),red)

# High-level walkways: two parallel fixed structures --------------------------
for yy in [-7.9,7.9]:
    group('East walkway' if yy<0 else 'West walkway','05 | High-level walkways')
    box((0,yy,43.5),(61.5,3.5,.65),blue)
    box((0,yy,48.35),(61.5,3.8,.38),ivory)
    box((0,yy,48.65),(61.5,3.85,.24),blue)
    box((0,yy,45.8),(61,2.9,4),glass)
    for side in [-1,1]:
        y=yy+side*1.83
        for z in [44,47.9]:beam((-30.8,y,z),(30.8,y,z),.24,lightblue)
        for i in range(16):
            x=-30.5+i*61/16; nx=-30.5+(i+1)*61/16
            beam((x,y,44),(x,y,47.9),.18,ivory)
            beam((x,y,44),(nx,y,47.9),.19,ivory)
            beam((x,y,47.9),(nx,y,44),.19,ivory)
        for xx in [-15.4,0,15.4]:
            box((xx,y,45.9),(2.5,.34,4.2),trim)
            cyl((xx,y+side*.23,46.2),.77,.18,gold,24,axis=(0,1,0))
            # Small red cross on the ceremonial shield.
            box((xx,y+side*.35,46.2),(1,.06,.16),red)
            box((xx,y+side*.35,46.2),(.16,.06,1.05),red)
    for i in range(20):
        xx=-29+i*3
        beam((xx,yy-1.6,43.12),(xx,yy+1.6,43.12),.17,ivory)

def road(start,end,local=False):
    cx=(start+end)/2; length=abs(end-start)
    box((cx,0,-.25),(length,15.6,.65),blue)
    box((cx,0,.11),(length,11.4,.16),asphalt)
    for yy in [-6.7,6.7]:
        box((cx,yy,.25),(length,2,.35),trim)
    count=max(1,int(length/3))
    for i in range(count):
        x=start+(end-start)*(i+.5)/count
        box((x,0,.202),(1.5,.13,.025),white)
    for yy in [-5.3,5.3]:box((cx,yy,.205),(length,.12,.025),white)
    for side in [-1,1]:
        y=side*7.65
        for z in [.5,1.6]:beam((start,y,z),(end,y,z),.14,blue)
        n=max(1,int(length/2.5))
        for i in range(n+1):
            x=start+(end-start)*i/n
            beam((x,y,.42),(x,y,1.75),.14,blue)
            sphere((x,y,1.8),.12,gold)
            if i<n:
                nx=start+(end-start)*(i+1)/n
                beam((x,y,.58),(nx,y,1.45),.085,ivory)
                beam((x,y,1.45),(nx,y,.58),.085,ivory)

# Permanent roadway is grouped under a fixed datum to keep the same local Z.
roadbase=empty('Road level | 10 m','06 | Roads',(0,0,10))
for start,end,name in [(-132,-30.5,'North fixed deck'),(30.5,132,'South fixed deck')]:
    group(name,'06 | Roads',roadbase); road(start,end)
    for yy in [-7.5,7.5]:
        for z in [-.65,-2.0]:beam((start,yy,z),(end,yy,z),.35,blue)
        n=int((end-start)/4)
        for i in range(n):
            x=start+(end-start)*i/n; nx=start+(end-start)*(i+1)/n
            beam((x,yy,-.65),(nx,yy,-2),.16,ivory)
            beam((x,yy,-2),(nx,yy,-.65),.16,ivory)

ctrl=empty('BRIDGE CONTROL | Opening degrees','07 | Bascule animation')
ctrl['Opening degrees']=0.0
ctrl.id_properties_ui('Opening degrees').update(min=0,max=CONFIG['opening_degrees'],description='Animated lift angle in degrees; both bascules follow this control.')
for f in range(1,END+1):
    deg=opening(f)
    ctrl['Opening degrees']=float(deg); ctrl.keyframe_insert(data_path='["Opening degrees"]',frame=f)
for sign,label in [(-1,'North'),(1,'South')]:
    pivot=empty(label+' bascule hinge','07 | Bascule animation',(sign*30.5,0,10))
    fc=pivot.driver_add('rotation_euler',1); dr=fc.driver; dr.type='SCRIPTED'; v=dr.variables.new();v.name='angle';v.type='SINGLE_PROP';v.targets[0].id=ctrl;v.targets[0].data_path='["Opening degrees"]'
    dr.expression=f'{sign} * angle * pi / 180'
    group(label+' moving bascule','07 | Bascule animation',pivot)
    end=-sign*30.44
    road(0,end)
    for yy in [-7.15,7.15]:
        beam((0,yy,-2.1),(end,yy,-.55),.38,blue)
        for i in range(10):
            x=end*i/10; nx=end*(i+1)/10
            z=-2.1+1.55*i/10; nz=-2.1+1.55*(i+1)/10
            beam((x,yy,-.58),(x,yy,z),.18,blue)
            beam((x,yy,z),(nx,yy,-.58),.15,ivory)
            beam((x,yy,-.58),(nx,yy,nz),.15,ivory)
    for i in range(11):
        x=end*i/11
        beam((x,-7.1,-.75),(x,7.1,-.75),.25,blue)
    for yy in [-7.9,7.9]:cyl((0,yy,-.1),.85,.55,gold,24,axis=(0,1,0))

# Side suspension chains and vertical hangers --------------------------------
for sign,label in [(-1,'North'),(1,'South')]:
    group(label+' suspension system','08 | Suspension chains')
    for side in [-1,1]:
        y=side*8.6
        def cable(t,upper=0):return(sign*(113-65*t),y,13.1+29.5*t*t+upper)
        for upper in [0,2.15]:polyline([cable(i/80,upper) for i in range(81)],.46,lightblue)
        for i in range(25):
            a=i/25;b=(i+1)/25
            beam(cable(a,0),cable(b,2.15),.13,ivory)
            beam(cable(a,2.15),cable(b,0),.13,ivory)
        for i in range(1,13):
            t=i/13;p=cable(t)
            beam((p[0],y,10.1),p,.25,ivory)
            box((p[0],y,11),(1,.8,.7),blue)
        cyl((sign*113,y,13.5),1.0,.7,blue,24,axis=(0,1,0))
        cyl((sign*113,y-side*.45,13.5),.46,.12,gold,24,axis=(0,1,0))

def lamp(x,y,z):
    cyl((x,y,z+.18),.32,.36,blue,12)
    cyl((x,y,z+1.8),.11,3.5,blue,12)
    for zz,rr in [(z+.6,.18),(z+2.9,.19),(z+3.3,.24)]:cyl((x,y,zz),rr,.18,gold,12)
    box((x,y,z+3.8),(.55,.55,.85),lampmat)
    for dx in [-.3,.3]:
        for dy in [-.3,.3]:beam((x+dx,y+dy,z+3.3),(x+dx,y+dy,z+4.25),.065,blue)
    cyl((x,y,z+4.38),.5,.32,blue,4,r2=.04)
    sphere((x,y,z+4.6),.11,gold)

group('Bridge lanterns','09 | Street furniture')
for x in [-124,-110,-96,-81,-64,64,81,96,110,124]:
    for y in [-7,7]:lamp(x,y,10.5)
group('Quayside lanterns','09 | Street furniture')
for a in ([] if CONFIG['features'].get('city') else [pi*.16,pi*.32,pi*.5,pi*.68,pi*.84,pi*1.16,pi*1.32,pi*1.68,pi*1.84]):lamp(140*cos(a),64.5*sin(a),2.7)

# A small sailing boat crosses only while the bridge is fully raised.
boat=empty('Sailing boat | crossing route','11 | River boat')
for f in range(1,END+1):
    y=boat_y(f)
    boat.location=(0,y,0);boat.keyframe_insert('location',frame=f)
group('Sailing boat hull and cabin','11 | River boat',boat)
outline=[(-1.9,-6),(-2.6,-3),(-2.4,4),(0,8),(2.4,4),(2.6,-3),(1.9,-6)]
v=[(x*.7,y*.95,.5) for x,y in outline]+[(x,y,2.1) for x,y in outline]
meshpart(v,[tuple(range(6,-1,-1)),tuple(range(7,14))]+[(i,(i+1)%7,(i+1)%7+7,i+7) for i in range(7)],ivory)
for i in range(7):beam(v[i+7],v[(i+1)%7+7],.14,gold)
box((0,-1,2.5),(3.1,5.5,.8),navy);box((0,-1,3),(3.3,5.6,.24),trim)
beam((0,.8,2.2),(0,.8,25),.20,slate)
beam((0,.8,5),(-5.7,.8,5),.16,slate)
group('Sailing canvas','11 | River boat',boat)
meshpart([(-.2,.85,24),(-5.65,.85,5.2),(-.2,.85,5.2)],[(0,1,2)],white)
meshpart([(.25,.85,22),(5.1,.85,4),(.25,.85,4)],[(0,1,2)],ivory)
group('Standing rigging','11 | River boat',boat)
for a,b in [((0,.8,24),(0,7.2,2.1)),((0,.8,24),(0,-5.5,2.1))]:beam(a,b,.035,gold)

# Extension components share the geometry batch API.
for component in ['traffic','city','river']:
    if CONFIG['features'].get(component):
        import importlib
        importlib.import_module('scene_components.'+component).build(globals())

# Flush all geometry into editable semantic meshes (hundreds, not thousands).
for (name,collection,parent,matname),(verts,faces,smooth,mat) in buckets.items():
    mesh=bpy.data.meshes.new(name+' mesh');mesh.from_pydata(verts,[],faces);mesh.materials.append(mat);mesh.update()
    obj=bpy.data.objects.new(name+' | '+matname.split('|')[0].strip(),mesh)
    coll(collection).objects.link(obj)
    if parent:obj.parent=parent
    for p,s in zip(mesh.polygons,smooth):p.use_smooth=s
    # Tiny chamfers catch highlights; masonry trim stays crisp and editable.
    if mat in [trim,blue,lightblue,red,navy,gold] and len(mesh.polygons)<18000:
        mod=obj.modifiers.new('Edge highlights','BEVEL');mod.width=.035;mod.segments=2

# A restrained museum label on the display plinth.
def text_obj(name,body,location,size,mat,rotation=(pi/2,0,0)):
    data=bpy.data.curves.new(name,'FONT');data.body=body;data.align_x='CENTER';data.align_y='CENTER';data.size=size;data.extrude=.012;data.bevel_depth=.004;data.materials.append(mat)
    obj=bpy.data.objects.new(name,data);coll('12 | Display lettering').objects.link(obj);obj.location=location;obj.rotation_euler=rotation
    return obj
text_obj('Title','T O W E R   B R I D G E',(0,-90.05,-3.1),2.25,gold)
text_obj('Subtitle','L O N D O N   /   1 8 9 4',(0,-90.1,-4.8),.76,ivory)

# Studio floor, lighting and cameras ------------------------------------------
mesh=bpy.data.meshes.new('floor');mesh.from_pydata([(-2000,-2000,-6.75),(2000,-2000,-6.75),(2000,2000,-6.75),(-2000,2000,-6.75)],[],[(0,1,2,3)]);mesh.materials.append(groundmat)
obj=bpy.data.objects.new('Studio floor',mesh);coll('13 | Lighting and cameras').objects.link(obj)

def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def area(name,loc,power,size,color,target):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    ob=bpy.data.objects.new(name,data);coll('13 | Lighting and cameras').objects.link(ob);ob.location=loc;aim(ob,target)
area('Key | warm softbox',(-80,-100,180),280000,110,(1,.86,.68),(0,0,12))
area('Fill | cool river sky',(100,40,130),220000,100,(.63,.81,1),(0,0,23))
area('Rim | tower silhouette',(-60,120,130),300000,85,(1,.94,.79),(0,0,32))
sun=bpy.data.lights.new('Afternoon sun','SUN');sun.energy=2.0;sun.angle=.12;sun.color=(1,.88,.73)
ob=bpy.data.objects.new('Afternoon sun',sun);coll('13 | Lighting and cameras').objects.link(ob);ob.rotation_euler=(.5,-.35,-.5)

def camera(name,loc,target,lens=48,ortho=None):
    data=bpy.data.cameras.new(name);data.lens=lens;data.clip_end=3000
    ob=bpy.data.objects.new(name,data);coll('13 | Lighting and cameras').objects.link(ob);ob.location=loc;aim(ob,target)
    if ortho:data.type='ORTHO';data.ortho_scale=ortho
    return ob
hero=camera('01 | Hero camera',(186,-278,174),(0,0,20),48,ortho=312)
detail=camera('02 | Architectural detail',(95,-114,78),(17,0,36),53)
front=camera('03 | Front elevation',(0,-350,40),(0,0,30),48,ortho=292)
anim=camera('04 | Animated camera',(170,-300,165),(0,0,21),48,ortho=314)
for f,angle in [(1,-66),(120,-62),(288,-73),(456,-99),(624,-107),(720,-112)]:
    a=math.radians(angle);anim.location=(340*cos(a),340*sin(a),172);aim(anim,(0,0,22))
    anim.keyframe_insert('location',frame=f);anim.keyframe_insert('rotation_euler',frame=f)
scene.camera=hero

for seconds,name in PHASES:scene.timeline_markers.new(name,frame=frame(seconds))
from scene_components import cameras
cameras.build(globals())
if CONFIG['features'].get('lighting'):
    from scene_components import lighting
    lighting.build(globals())
from scene_components import finish
finish.build(globals())
linear_keys()

readme='''TOWER BRIDGE / LONDON 1894
Original procedural architectural study created in Blender.
No geometry or textures from the supplied FBX or GLB were used in this project.
Architectural proportions and details are an artistic reconstruction, not surveyed drawings.

PLAY: Space in the Timeline. Animation: frames 1-1440, 24 fps (60 s).
Frame 1: day/closed. Frame 720: ship/open. Frame 1440: blue hour/closed.
Control: select BRIDGE CONTROL | Opening degrees and inspect Object > Custom Properties.
Both moving decks are children of hinge empties driven by the control.
The two upper walkways and side suspension spans remain fixed.
Camera 01: static hero. Camera 02: detail. Camera 03: elevation. Camera 04: animated.
All materials are procedural or constant-color: no external texture files required.
Collections divide the scene by structural component. Semantic meshes can be edited in Edit Mode.
To separate individual loose pieces: Edit Mode > select > P > By Loose Parts.

REFERENCES (viewed 2026-10-14):
https://www.towerbridge.org.uk/stories/what-type-of-bridge-is-tower-bridge
https://www.towerbridge.org.uk/stories/the-architectural-style-of-tower-bridge
https://www.towerbridge.org.uk/explore-inside
https://3dtudor.gumroad.com/l/London_Bridge_Blender_Unreal_Engine
https://www.youtube.com/watch?v=kdWINtbofzo
3D Tudor provided the visual idea of a bridge diorama; the paid project was not downloaded.
YouTube transcript was unavailable; the full tutorial was not reviewed.
'''
txt=bpy.data.texts.new('START HERE | Project notes');txt.write(readme)
scene['Project']='Tower Bridge | architectural diorama'
scene['Construction']='Original generated geometry; artistic reconstruction'
scene['Animation']=f'{END} frames / {FPS} fps / deterministic scenario'
scene['Configuration']=json.dumps(CONFIG,sort_keys=True)
scene.frame_set(frame(30))
# Open the file in a useful camera view, with uncluttered material-colored geometry.
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':
            ar.spaces.active.region_3d.view_perspective='CAMERA'
            ar.spaces.active.shading.color_type='MATERIAL'
            ar.spaces.active.overlay.show_extras=False
            ar.spaces.active.clip_end=3000
scene.render.filepath=str(OUT/'renders'/'Tower_Bridge_Hero.png')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Tower_Bridge.blend'))
stats={'objects':len(bpy.data.objects),'mesh_objects':sum(o.type=='MESH' for o in bpy.data.objects),'vertices':sum(len(m.vertices) for m in bpy.data.meshes),'faces':sum(len(m.polygons) for m in bpy.data.meshes),'materials':len(bpy.data.materials),'frames':END,'fps':FPS}
(OUT/'scene_statistics.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
(OUT/'SOURCES.txt').write_text(readme,encoding='utf-8')
print('BUILD_OK',json.dumps(stats),flush=True)

if '--preview' in sys.argv:
    scene.render.engine='CYCLES';scene.cycles.samples=24
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for dev in prefs.devices:dev.use=dev.type=='OPTIX'
        scene.cycles.device='GPU'
    except Exception as e:print('GPU setup:',e)
    scene.render.resolution_percentage=60
    scene.render.filepath=str(OUT/'renders'/'preview.png')
    bpy.ops.render.render(write_still=True)
    print('PREVIEW_OK',flush=True)
