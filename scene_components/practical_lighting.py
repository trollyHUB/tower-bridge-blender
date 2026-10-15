"""Configurable practical lighting for streets, walkways, docks and social spaces."""
from .scenario import CONFIG, END, dusk, frame

def build(g):
    bpy=g['bpy'];scene=g['scene'];cfg=CONFIG['lighting']
    def keyed(data,path,day,night):
        for f in [1,frame(50),frame(53),frame(56),END]:
            value=day*cfg['day_strength']*(1-dusk(f))+night*cfg['night_strength']*dusk(f)
            setattr(data,path,value);data.keyframe_insert(path,frame=f)
    def source(name,role,loc,power,target=None,color=(1,.57,.23),size=1):
        data=bpy.data.lights.new(name,'AREA' if target else 'POINT');data.color=color
        if target:data.shape='DISK';data.size=size
        else:data.shadow_soft_size=.6;data.use_shadow=False
        ob=bpy.data.objects.new(name,data);g['coll']('Lighting | '+role).objects.link(ob)
        ob.location=loc;ob['lighting_role']=role
        if target:g['aim'](ob,target)
        keyed(data,'energy',0,power);return ob
    for light in list(bpy.data.lights):
        if 'headlight ' in light.name:continue
        if light.type=='SUN':keyed(light,'energy',2,.32)
        elif light.type=='AREA':keyed(light,'energy',light.energy,light.energy*.30)
    bg=scene.world.node_tree.nodes['Background']
    for f in [1,frame(50),frame(53),frame(56),END]:
        bg.inputs['Strength'].default_value=.35*cfg['day_strength']*(1-dusk(f))+.18*cfg['night_strength']*dusk(f)
        bg.inputs['Strength'].keyframe_insert('default_value',frame=f)
    locations=[(x,y,14.3) for x in [-124,-110,-96,-81,-64,64,81,96,110,124] for y in [-7,7]]
    locations += [(sign*x,y,14.05) for sign in [-1,1] for x in [115,132,150,169,196] for y in [-7,7]]
    for i,loc in enumerate(locations):source('Practical lantern %02d'%i,'lantern',loc,cfg['lantern_power'])
    for x in [-39,39]:
        for y in [-20,20]:source('Tower floodlight','tower',(x,y,8),cfg['tower_power'],(x,0,36),size=8)
        source('Upper tower wash','tower',(x,-32,48),cfg['tower_power']*1.55,(x,0,43),(.55,.72,1),16)
    for x in [-20,0,20]:
        for y in [-7.9,7.9]:source('Walkway architectural light','walkway',(x,y,43.0),cfg['walkway_power'],(x,y,47),(.55,.76,1),4)
    for sign in [-1,1]:
        for y in [29,41]:source('Dock lantern','dock',(sign*103,y,5.0),cfg['dock_power'])
        source('Bus shelter interior','bus_stop',(sign*157,9.4,12.8),cfg['stop_power'],(sign*157,9.4,10.3),size=2)
    for x in [-151,-143]:source('Cafe terrace light','cafe',(x,19,14),cfg['cafe_power'],(x,18,10.3),size=2)
    for mat in bpy.data.materials:
        if not mat.use_nodes:continue
        bs=mat.node_tree.nodes.get('Principled BSDF')
        if bs and ('occupied window' in mat.name or mat==g['lampmat']):
            for f in [1,frame(50),frame(53),frame(56),END]:
                bs.inputs['Emission Strength'].default_value=.1+3*dusk(f)
                bs.inputs['Emission Strength'].keyframe_insert('default_value',frame=f)
