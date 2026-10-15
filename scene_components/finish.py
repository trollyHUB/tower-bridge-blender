"""Material aging, cloth motion, mesh sharing and useful file defaults."""
import math, hashlib
from .scenario import END, FPS, CONFIG

def build(g):
    bpy=g['bpy']
    for mat in [g['asphalt'],g['blue'],g['foundation']]:
        tree=mat.node_tree;bs=tree.nodes.get('Principled BSDF')
        noise=tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=9 if mat==g['asphalt'] else 2
        bump=tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.035
        tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    # Darkening at river level uses true world height, not per-mesh generated UVs.
    tree=g['foundation'].node_tree;bs=tree.nodes.get('Principled BSDF')
    geo=tree.nodes.new('ShaderNodeNewGeometry');sep=tree.nodes.new('ShaderNodeSeparateXYZ')
    ramp=tree.nodes.new('ShaderNodeMapRange');ramp.inputs['From Min'].default_value=0;ramp.inputs['From Max'].default_value=5
    mix=tree.nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.065,.10,.08,1);mix.inputs[2].default_value=(.30,.33,.32,1)
    tree.links.new(geo.outputs['Position'],sep.inputs[0]);tree.links.new(sep.outputs['Z'],ramp.inputs['Value']);tree.links.new(ramp.outputs[0],mix.inputs[0]);tree.links.new(mix.outputs[0],bs.inputs['Base Color'])
    for ob in list(bpy.data.objects):
        if ob.type!='MESH':continue
        if ' flag |' in ob.name or ob.name.startswith('Sailing canvas'):
            ob.shape_key_add(name='Basis');key=ob.shape_key_add(name='Wind | cloth ripple')
            for vertex in key.data:
                x,y,z=vertex.co
                vertex.co.y += .22*math.sin(x*2+z*.7)
            for f in sorted(set([1,END]+list(range(1,END+1,8)))):
                key.value=.5+.5*math.sin(f/FPS*2.4);key.keyframe_insert('value',frame=f)
    # Link identical local meshes (wheels, crowns, articulated limbs).
    seen={};linked=0
    for ob in list(bpy.data.objects):
        if ob.type!='MESH' or ob.data.shape_keys:continue
        mesh=ob.data
        signature=(tuple(tuple(round(c,5) for c in v.co) for v in mesh.vertices),
                   tuple(tuple(p.vertices) for p in mesh.polygons),tuple(m.name for m in mesh.materials))
        if signature in seen:
            ob.data=seen[signature];linked+=1
        else:seen[signature]=mesh
    g['scene']['Linked repeated meshes']=linked
    g['scene']['Version']=CONFIG['version']
