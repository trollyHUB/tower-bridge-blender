"""Two connected London banks, generated with the shared geometry batcher."""
import math
import random
from .scenario import CONFIG, END, FPS, frame as timeline_frame
from .people_math import route_state, foot_target, leg_angles
from .wind import wind_vector


def build(g):
    box, beam, cyl, sphere = (g[k] for k in ('box', 'beam', 'cyl', 'sphere'))
    group, material, empty = (g[k] for k in ('group', 'material', 'empty'))
    stone, trim, dark, glass, slate, blue, gold, white, asphalt = (
        g[k] for k in ('stone', 'trim', 'dark', 'glass', 'slate', 'blue', 'gold', 'white', 'asphalt'))
    pavement = material('City | warm paving', (.43,.42,.37), rough=.88)
    brick = material('City | red London stock brick', (.36,.13,.075), rough=.83)
    cream = material('City | cream stucco', (.70,.63,.46), rough=.78)
    ochre = material('City | ochre terraces', (.48,.31,.15), rough=.8)
    wood = material('City | quay oak', (.22,.12,.055), rough=.8)
    leaf = material('City | plane tree leaves', (.14,.28,.07), rough=.9)
    grass = material('City | riverside lawn', (.16,.24,.08), rough=.95)
    red = g['red']
    lit = material('City | occupied window amber', (.48,.29,.105), rough=.32)
    bs=lit.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Emission Color'].default_value=(.8,.42,.12,1)
    bs.inputs['Emission Strength'].default_value=.45
    rng=random.Random(CONFIG['seed'])
    glazing=[material('City | glazing variant %d'%i,
                      (.12+rng.random()*.10,.22+rng.random()*.12,.27+rng.random()*.13),
                      rough=.12+rng.random()*.24) for i in range(12)]
    ground=10.2

    def label(text, loc, size=.8, rotation=(math.pi/2,0,0)):
        bpy=g['bpy']; curve=bpy.data.curves.new(text,'FONT'); curve.body=text
        curve.align_x='CENTER'; curve.size=size; curve.extrude=.015
        ob=bpy.data.objects.new(text,curve); g['coll']('City | signage').objects.link(ob)
        ob.location=loc; ob.rotation_euler=rotation; curve.materials.append(trim)

    def bench(x,y):
        for yy in [-.25,0,.25]:box((x,y+yy,10.82),(2.3,.17,.13),wood)
        for xx in [-.85,.85]:
            box((x+xx,y,10.55),(.12,.65,.65),blue)
            beam((x+xx,y+.27,10.6),(x+xx,y+.4,11.6),.09,blue)
        box((x,y+.4,11.35),(2.3,.12,.45),wood)

    # Road surface and pavement meet the existing approach at x=110.
    for sign in [-1,1]:
        group('Bank infrastructure '+str(sign),'City | streets')
        box((sign*160,0,5.0),(100,136,10),stone)
        box((sign*160,0,10.1),(100,136,.2),pavement)
        box((sign*160,0,10.23),(100,11.4,.08),asphalt)
        box((sign*185,0,10.24),(11.4,136,.09),asphalt)
        for x in range(113,210,8):
            if abs(x-185)>10:box((sign*x,0,10.3),(3,.16,.025),white)
        for y in range(-64,65,8):
            if abs(y)>10:box((sign*185,y,10.31),(.16,3,.025),white)
        for y in [-7,7]:
            for x in [115,132,150,169,196]:g['lamp'](sign*x,y,10.25)
        # A covered street end conceals traffic recycling from every city camera.
        # Internal walls start at |y|7.8; a double-decker clears the roof at z16.
        box((sign*214.5,0,5),(9,19.2,10),stone)
        box((sign*209,0,10.23),(20,11.4,.08),asphalt)
        for yy in [-6.7,6.7]:
            box((sign*209,yy,10.25),(20,2,.3),pavement)
        for yy in [-8.7,8.7]:
            box((sign*209,yy,13.1),(20,1.8,5.8),brick)
            box((sign*199,yy,13.1),(1,2.2,5.8),trim)
        box((sign*209,0,17),(20,19.2,2),stone)
        box((sign*219,0,13.1),(1,19.2,5.8),dark)
        box((sign*198.9,0,17),( .35,14.8,1.3),blue)
        label('LONDON',(sign*198.68,0,16.65),.9,
              (math.pi/2,0,-sign*math.pi/2))
        # Tactile curbs, connected east-west sidewalks, crosswalks and bollards.
        for y in [-5.95,5.95]:
            box((sign*144.5,y,10.34),(69,.35,.3),trim)
            box((sign*200.5,y,10.34),(19,.35,.3),trim)
        for dy in [-10,10]:
            for x in range(181,190,2):box((sign*x,dy,10.31),(1,3,.025),white)
        for x in [176,194]:
            for y in [-4,-2,0,2,4]:box((sign*x,y,10.31),(2.4,.9,.025),white)
        for y in [-14,14]:
            for x in [177,193]:cyl((sign*x,y,10.8),.15,1.1,blue,10)
        # Bus stop shelter, lay-by markings and roundel.
        sx=sign*157
        for xx in [-3,3]:
            for yy in [8.3,10.7]:cyl((sx+xx,yy,11.6),.075,2.8,blue,8)
        box((sx,10.7,11.7),(6,.08,2.4),glass)
        box((sx,9.5,13.1),(7,3.2,.22),blue)
        bench(sx,10)
        cyl((sign*163,8,12),.07,3.6,blue,8)
        cyl((sign*163,8,13.5),.6,.12,red,24,axis=(0,1,0))
        box((sign*163,7.91,13.5),(1.3,.08,.24),blue)
        for x in [151,155,159,163]:box((sign*x,4.9,10.3),(2.5,.12,.025),g['gold'])
        for y in [-12,12,55,-55]:
            bench(sign*119,y)
            cyl((sign*122,y,10.75),.38,.95,blue,12)
            cyl((sign*122,y,11.24),.42,.08,gold,12)
        for x in [140,142,144]:
            beam((sign*x,-10,10.3),(sign*x,-10,11.2),.07,blue)
            beam((sign*x,-11,10.3),(sign*x,-11,11.2),.07,blue)
            beam((sign*x,-10,11.2),(sign*x,-11,11.2),.07,blue)
        # Quay wall, capstones and railings, with a staircase opening.
        # Leave an actual masonry opening for the descending quay stair.
        box((sign*110,-18.5,6.1),(2,99,8),stone)
        box((sign*110,53.5,6.1),(2,29,8),stone)
        for y in range(-66,67,3):
            if abs(y)<10 or 29<y<41:continue
            box((sign*110,y,10.35),(2.5,2.8,.35),trim)
            cyl((sign*110,y,11.05),.07,1.3,blue,8)
            if y<64:beam((sign*110,y,11.65),(sign*110,y+3,11.65),.065,blue)
        for i in range(16):
            z=10.2-i*.49
            box((sign*(110-i*.48),35,z-.25),(1.1,8,.5),stone)
        box((sign*101.8,35,2.45),(7.5,16,.5),wood)
        for y in [28,42]:
            for x in [99,105]:cyl((sign*x,y,1.4),.22,3.4,wood,12)
        # Parking bays sit clear of the main traffic and crossing.
        for y in [-48,-42,-36]:
            for yy in [y-2.5,y+2.5]:box((sign*198,yy,10.31),(6,.1,.025),white)
            box((sign*201,y,10.31),(.1,5,.025),white)

    # Eight recognisable building types, all doors start on pavement level.
    plans=[(-145,-29,22,21,17,brick,'RIVERSIDE STORES'),
           (-169,-46,17,25,22,cream,'THE BRIDGE HOTEL'),
           (-143,32,25,22,15,ochre,'THAMES CAFE'),
           (-166,48,18,23,19,brick,'ALBERT TERRACE'),
           (145,-30,25,23,18,brick,'BUTLERS WHARF'),
           (165,-52,18,19,14,stone,'RIVER WORKSHOPS'),
           (145,38,22,20,21,cream,'ST KATHARINE HOUSE'),
           (169,42,17,29,16,ochre,'DOCKSIDE GALLERY')]
    for index,(x,y,w,d,h,wall,name) in enumerate(plans):
        group(name,'City | buildings')
        box((x,y,ground+h/2),(w,d,h),wall)
        for z in [ground+.3,ground+3.8,ground+h-.4]:box((x,y,z),(w+.5,d+.5,.35),trim)
        box((x,y,ground+h+.3),(w+1,d+1,.6),slate)
        front=y-d/2
        for row in range(1,int(h/3.7)):
            for col in range(max(2,int(w/3.5))):
                xx=x-w/2+2+col*3.5; z=ground+2+row*3.2
                if xx>x+w/2-1:continue
                box((xx,front-.08,z),(1.65,.2,2.1),trim)
                box((xx,front-.2,z),(1.35,.12,1.8),lit if (row+col+index)%5==0 else glazing[(index*3+row+col)%len(glazing)])
                box((xx,front-.29,z),(.07,.08,1.8),trim)
                box((xx,front-.29,z),(1.35,.08,.07),trim)
                box((xx,front-.3,z-1.12),(1.85,.5,.13),trim)
        # Side elevation repeats the framed rhythm to read in three-quarter views.
        for yy in range(int(y-d/2+3),int(y+d/2-1),4):
            for z in range(15,int(ground+h-1),4):
                box((x+w/2+.06,yy,z),(.16,1.7,2.2),trim)
                box((x+w/2+.16,yy,z),(.08,1.4,1.9),glass)
        box((x,front-.16,11.65),(1.7,.22,2.9),wood)
        box((x+.55,front-.32,11.6),(.08,.07,.5),gold)
        if index in [0,2,7]:
            for dx in [-w*.29,w*.29]:box((x+dx,front-.2,11.8),(w*.3,.2,2.5),glass)
            for k in range(12):box((x-w/2+(k+.5)*w/12,front-.8,13.65),(w/12,1.8,.18),cream if k%2 else blue)
        if index in [4,5]:
            box((x+w*.26,front-.17,12.1),(4,.22,3.8),wood)
            for z in [10.7,11.3,11.9,12.5,13.1,13.7]:box((x+w*.26,front-.3,z),(4,.06,.06),dark)
        box((x,front-.22,14),(w*.85,.22,1),blue)
        label(name,(x,front-.38,13.74),.58)
        for dx in [-w*.3,w*.3]:
            box((x+dx,y,ground+h+1),(1.1,1.2,2.1),wall)
            box((x+dx,y,ground+h+2.1),(1.4,1.5,.25),trim)
        # Exposed gutters and downpipes keep the roof silhouette varied.
        beam((x-w/2,front-.32,ground+h),(x+w/2,front-.32,ground+h),.12,blue)
        for dx in [-w/2+.3,w/2-.3]:
            cyl((x+dx,front-.38,ground+h/2),.075,h,blue,8)
        if index in [1,3,6]:
            for z in [17.1,20.3]:
                if z+1>ground+h:continue
                box((x,front-.75,z-.95),(w*.62,1.5,.18),trim)
                for xx in range(int(x-w*.30),int(x+w*.30)+1):
                    beam((xx,front-1.4,z-.9),(xx,front-1.4,z+.12),.055,blue)
                beam((x-w*.31,front-1.4,z+.12),(x+w*.31,front-1.4,z+.12),.08,blue)

    # Park with wind-moving tree crowns; all trunks stay on the banks.
    for sign in [-1,1]:
        group('Riverside pocket gardens '+str(sign),'City | gardens')
        box((sign*123,51,10.28),(17,27,.16),grass)
        for i,(x,y) in enumerate([(119,43),(129,55),(119,61),(203,55),(203,22),(124,-57)]):
            x*=sign
            cyl((x,y,12.1),.28,3.8,wood,10)
            crown=empty('Wind crown %s %s'%(sign,i),'City | gardens',(x,y,13.5))
            group('Plane tree crown %s %s'%(sign,i),'City | gardens',crown)
            for dx,dy,dz,r in [(0,0,.8,2.7),(-1.1,.3,.4,1.9),(1.2,-.4,1.3,1.9)]:sphere((dx,dy,dz),r,leaf)
            for f in sorted(set([1,END]+list(range(1,END+1,max(1,round(FPS*2)))))):
                wx,wy=wind_vector(f/FPS)[:2]
                crown.rotation_euler[0]=-wy*.21
                crown.rotation_euler[1]=wx*.21
                crown.keyframe_insert('rotation_euler',frame=f)
            group('Park furniture '+str(sign),'City | gardens')
        for yy in [42,53,62]:bench(sign*133,yy)

    # Low-poly articulated people walk only along the clear quay promenade.
    skin=material('People | skin',(.54,.32,.20),rough=.75)
    coats=[material('People | coat '+str(i),c,rough=.8) for i,c in enumerate([(.15,.23,.34),(.5,.15,.09),(.21,.32,.22),(.52,.39,.12)])]
    gait_cycle=2*CONFIG.get('people',{}).get('stride_length',.65)
    def person(i, keys, angle, route, moving):
        actor=empty('Walker %02d'%i,'Actors | pedestrians',keys[0][1])
        actor['route']=route; actor['actor_type']='person'; actor['role']='walker'
        actor['gait']='distance-driven two-segment legs with planted stance'
        gait_offset=((i*.38196601125+CONFIG['seed']*.001)%1)*gait_cycle
        actor['gait_phase_offset_m']=gait_offset
        actor.rotation_euler[2]=angle
        group('Walker %02d body'%i,'Actors | pedestrians',actor)
        box((0,0,1.05),(.42,.27,.58),coats[i%4]); sphere((0,0,1.55),.19,skin)
        limbs=[]
        for side in [-1,1]:
            hip=empty('Walker %02d leg %s'%(i,side),'Actors | pedestrians')
            hip.parent=actor; hip.location=(side*.12,0,.76)
            group('Walker %02d thigh %s'%(i,side),'Actors | pedestrians',hip)
            box((0,0,-.215),(.13,.15,.43),dark)
            knee=empty('Walker %02d shin %s'%(i,side),'Actors | pedestrians')
            knee.parent=hip; knee.location=(0,0,-.43)
            group('Walker %02d shin mesh %s'%(i,side),'Actors | pedestrians',knee)
            box((0,0,-.215),(.12,.14,.43),dark)
            foot=empty('Walker %02d foot %s'%(i,side),'Actors | pedestrians')
            foot.parent=knee; foot.location=(0,0,-.43)
            foot['actor_owner']=actor.name; foot['side']=side
            foot['gait_cycle']=gait_cycle; foot['stance_fraction']=.60
            group('Walker %02d shoe %s'%(i,side),'Actors | pedestrians',foot)
            box((0,.065,.035),(.16,.29,.07),dark)
            arm=empty('Walker %02d arm %s'%(i,side),'Actors | pedestrians')
            arm.parent=actor; arm.location=(side*.29,0,1.3)
            group('Walker %02d sleeve %s'%(i,side),'Actors | pedestrians',arm)
            box((0,0,-.31),(.13,.15,.62),coats[i%4])
            limbs.append((side,hip,knee,foot,arm))
        # Per-frame analytic targets preserve contact during every stance and wait.
        for f in range(1,END+1):
            loc,distance=route_state(keys,f)
            actor.location=loc; actor.keyframe_insert('location',frame=f)
            actor['route_distance']=distance; actor.keyframe_insert(data_path='["route_distance"]',frame=f)
            for side,hip,knee,foot,arm in limbs:
                target,lift=foot_target(distance+gait_offset,side,cycle=gait_cycle)
                target-=gait_offset
                if not moving(f):lift=0.0
                phase=((distance+gait_offset+(gait_cycle*.5 if side>0 else 0))/gait_cycle)%1
                for prop,value in [('stance',int(phase<=.60 or not moving(f))),('stance_anchor',target),('lift',lift)]:
                    foot[prop]=value; foot.keyframe_insert(data_path='["%s"]'%prop,frame=f)
                upper,lower=leg_angles(target-distance,lift)
                hip.rotation_euler[0]=upper; knee.rotation_euler[0]=lower
                foot.rotation_euler[0]=-upper-lower
                arm.rotation_euler[0]=-.25*math.sin((distance+gait_offset)/gait_cycle*2*math.pi)*side if moving(f) else 0
                for ob in (hip,knee,foot,arm):ob.keyframe_insert('rotation_euler',frame=f)
        return actor

    # Alternate north/south lanes so adjacent bodies stay well separated.
    bank_count=max(0,min(12,int(CONFIG.get('people',{}).get('bank_walkers',8))))
    left_count=(bank_count+1)//2
    for i in range(bank_count):
        sign=-1 if i<left_count else 1
        lane=i if sign<0 else i-left_count
        count=left_count if sign<0 else bank_count-left_count
        x=sign*(114.3+(3.15*lane/max(1,count-1)))
        north=lane%2==0
        ya,yb=(-61,-17) if not north else (17,61)
        person(i,[(1,(x,ya,10.3)),(END,(x,yb,10.3))],0,
               'Safe bank promenade; y stays outside road and stop area',lambda f:True)

    # Two people clear the moving leaf early, wait on the fixed approach,
    # then continue away from the bridge after the pedestrian gates open.
    clear=timeline_frame(13.34); resume=timeline_frame(46)
    for i,sign in enumerate([-1,1],bank_count):
        person(i,[(1,(sign*29,sign*6.05,10.43)),
                  (clear,(sign*55,sign*6.05,10.43)),
                  (resume,(sign*55,sign*6.05,10.43)),
                  (END,(sign*76,sign*6.05,10.43))],
               -sign*math.pi/2,'Bascule clearance before gates; wait at fixed x55 until 46 seconds',
               lambda f:f<clear or f>resume)
    def visitor(name,location,role,seated=False,angle=0):
        actor=empty(name,'Actors | pedestrians',location)
        actor['actor_type']='person'; actor['role']=role
        actor.rotation_euler[2]=angle
        group(name+' body','Actors | pedestrians',actor)
        hip=.48 if seated else .76
        box((0,0,hip+.29),(.42,.27,.58),coats[len(name)%4])
        sphere((0,0,hip+.8),.19,skin)
        for side in [-1,1]:
            beam((side*.27,0,hip+.5),(side*.29,.1,hip+.02),.075,coats[len(name)%4])
            if seated:
                beam((side*.12,0,hip),(side*.12,.38,hip),.075,dark)
                beam((side*.12,.38,hip),(side*.12,.38,.07),.07,dark)
                box((side*.12,.46,.055),(.16,.28,.11),dark)
            else:
                beam((side*.12,0,hip),(side*.12,0,.08),.075,dark)
                box((side*.12,.06,.055),(.16,.28,.11),dark)
        return actor

    # Waiting passengers occupy the shelter sidewalk, outside the road envelope.
    passenger_count=CONFIG.get('people',{}).get('passengers_per_stop',3)
    for sign in [-1,1]:
        for j in range(passenger_count):
            visitor('Bus passenger %s %02d'%(sign,j),(sign*157+(j-(passenger_count-1)/2)*.85,9.5,10.3),
                    'bus_stop_waiting',angle=math.pi)
    # Cafe frontage is y=21; seating lies between y=16 and 20, away from quay.
    for j in range(CONFIG.get('people',{}).get('cafe_visitors',4)):
        x=-151+(j//2)*8; y=18.0
        group('Cafe table %02d'%j,'City | furniture')
        if j%2==0:
            cyl((x,y,11.12),.73,.12,wood,24)
            cyl((x,y,10.73),.065,.8,blue,12)
        dx=-1.15 if j%2==0 else 1.15
        cx=x+dx
        chair=empty('Cafe chair %02d'%j,'City | furniture')
        chair['seat_owner']='Cafe visitor %02d'%j
        group('Cafe chair %02d'%j,'City | furniture',chair)
        box((cx,y,10.76),(.6,.6,.12),wood)
        for ox in [-.23,.23]:
            for oy in [-.23,.23]:beam((cx+ox,y+oy,10.3),(cx+ox,y+oy,10.72),.04,blue)
        box((cx+(.28 if dx>0 else -.28),y,11.08),(.09,.6,.55),wood)
        visitor('Cafe visitor %02d'%j,(cx,y,10.3),'cafe_seated',True,
                angle=math.pi/2 if dx>0 else -math.pi/2)
    g['scene']['Pedestrian walking count']=bank_count+2
    g['scene']['Pedestrian waiting count']=passenger_count*2
    g['scene']['Pedestrian cafe count']=CONFIG.get('people',{}).get('cafe_visitors',4)
    g['scene']['City buildings']=8
    g['scene']['Pedestrian route note']='%d bank walkers keep |y|>=17. Two bridge walkers clear leaves before gate closure and wait at |x|55 until 46 seconds.'%bank_count
    group('City completed','City | streets')
