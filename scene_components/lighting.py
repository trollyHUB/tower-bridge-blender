"""Baked daylight-to-blue-hour lighting; no external handlers needed."""
from .scenario import END, dusk, frame

def build(g):
    bpy=g['bpy'];scene=g['scene']
    def keyed(data,path,day,night):
        for f in [1,frame(50),frame(53),frame(56),END]:
            setattr(data,path,day+(night-day)*dusk(f));data.keyframe_insert(path,frame=f)
    for light in list(bpy.data.lights):
        if light.type=='SUN':keyed(light,'energy',2,.32)
        elif light.type=='AREA':keyed(light,'energy',light.energy,light.energy*.30)
    bg=scene.world.node_tree.nodes['Background']
    for f in [1,frame(50),END]:
        bg.inputs['Strength'].default_value=.35-.17*dusk(f);bg.inputs['Strength'].keyframe_insert('default_value',frame=f)
    locations=[(x,y,14.3) for x in [-124,-110,-96,-81,-64,64,81,96,110,124] for y in [-7,7]]
    locations += [(sign*x,y,14.05) for sign in [-1,1] for x in [132,150,169,196] for y in [-7,7]]
    for i,loc in enumerate(locations):
        data=bpy.data.lights.new('Practical lantern %02d'%i,'POINT');data.color=(1,.57,.23);data.shadow_soft_size=.65
        # The stylised glass is opaque geometry; avoid self-shadowing inside it.
        data.use_shadow=False
        ob=bpy.data.objects.new(data.name,data);g['coll']('Lighting | practical lanterns').objects.link(ob);ob.location=loc
        keyed(data,'energy',0,650)
    for x in [-39,39]:
        for y in [-20,20]:
            data=bpy.data.lights.new('Tower floodlight','AREA');data.shape='DISK';data.size=8;data.color=(1,.67,.33)
            ob=bpy.data.objects.new(data.name,data);g['coll']('Lighting | architecture').objects.link(ob);ob.location=(x,y,8);g['aim'](ob,(x,0,36));keyed(data,'energy',0,4200)
    for x in [-39,39]:
        data=bpy.data.lights.new('Upper tower wash','AREA');data.size=16;data.color=(.55,.72,1)
        ob=bpy.data.objects.new(data.name,data);g['coll']('Lighting | architecture').objects.link(ob);ob.location=(x,-32,48);g['aim'](ob,(x,0,43));keyed(data,'energy',0,6500)
    for mat in bpy.data.materials:
        if not mat.use_nodes:continue
        bs=mat.node_tree.nodes.get('Principled BSDF')
        if bs and ('occupied window' in mat.name or mat==g['lampmat']):
            for f in [1,frame(50),END]:
                bs.inputs['Emission Strength'].default_value=.1+3*dusk(f);bs.inputs['Emission Strength'].keyframe_insert('default_value',frame=f)
