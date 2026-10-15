"""Material aging, cloth motion, mesh sharing and useful file defaults."""
import math
from .scenario import END, FPS, CONFIG
from .wind import wind_vector, wind_time

def build(g):
    bpy=g['bpy']
    def surface_wear(mat, scale, rough_low, rough_high, depth):
        tree=mat.node_tree; bs=tree.nodes.get('Principled BSDF')
        base=tuple(bs.inputs['Base Color'].default_value)
        geo=tree.nodes.new('ShaderNodeNewGeometry')
        noise=tree.nodes.new('ShaderNodeTexNoise'); noise.name='Wear | world-space grain'
        noise.inputs['Scale'].default_value=scale
        noise.inputs['Detail'].default_value=3
        tree.links.new(geo.outputs['Position'],noise.inputs['Vector'])
        rough=tree.nodes.new('ShaderNodeMapRange'); rough.name='Wear | roughness variation'
        rough.inputs['To Min'].default_value=rough_low; rough.inputs['To Max'].default_value=rough_high
        tree.links.new(noise.outputs['Fac'],rough.inputs['Value'])
        tree.links.new(rough.outputs[0],bs.inputs['Roughness'])
        color=tree.nodes.new('ShaderNodeMixRGB'); color.name='Wear | faded and darkened finish'
        color.inputs[1].default_value=tuple(c*.68 for c in base[:3])+(1,)
        color.inputs[2].default_value=tuple(min(1,c*1.12+.015) for c in base[:3])+(1,)
        tree.links.new(noise.outputs['Fac'],color.inputs[0]); tree.links.new(color.outputs[0],bs.inputs['Base Color'])
        bump=tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.18
        bump.inputs['Distance'].default_value=depth
        tree.links.new(noise.outputs['Fac'],bump.inputs['Height']); tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
        return geo,noise,bump

    for name,scale,lo,hi,depth in [('asphalt',9,.77,.98,.035),('blue',2,.28,.55,.018),
                                  ('lightblue',2.8,.25,.48,.014)]:
        surface_wear(g[name],scale,lo,hi,depth)
    # Fine world-space mortar gives block joints their own recessed dark material.
    for mat in [g['stone'],g['foundation']]:
        geo,noise,bump=surface_wear(mat,2.2,.72,.94,.045)
        tree=mat.node_tree;bs=tree.nodes.get('Principled BSDF')
        base=tuple(bs.inputs['Base Color'].default_value)
        brick=tree.nodes.new('ShaderNodeTexBrick'); brick.name='Stone | recessed dirty mortar'
        brick.inputs['Scale'].default_value=1.0
        brick.inputs['Brick Width'].default_value=2.4
        brick.inputs['Row Height'].default_value=.85
        brick.inputs['Mortar Size'].default_value=.035
        brick.inputs['Mortar Smooth'].default_value=.02
        brick.inputs['Color1'].default_value=tuple(c*.8 for c in base[:3])+(1,)
        brick.inputs['Color2'].default_value=tuple(min(1,c*1.1) for c in base[:3])+(1,)
        brick.inputs['Mortar'].default_value=(.12,.115,.095,1)
        tree.links.new(geo.outputs['Position'],brick.inputs['Vector'])
        tree.links.new(brick.outputs['Color'],bs.inputs['Base Color'])
        joint=tree.nodes.new('ShaderNodeBump'); joint.name='Stone | recessed joints'
        joint.inputs['Strength'].default_value=.35; joint.inputs['Distance'].default_value=.055
        joint.invert=True
        tree.links.new(brick.outputs['Fac'],joint.inputs['Height'])
        tree.links.new(bump.outputs['Normal'],joint.inputs['Normal'])
        tree.links.new(joint.outputs['Normal'],bs.inputs['Normal'])
    # Window variation is connected to the shader, including the shared glass.
    for mat in [m for m in bpy.data.materials if m==g['glass'] or 'glazing variant' in m.name]:
        tree=mat.node_tree;bs=tree.nodes.get('Principled BSDF')
        base=tuple(bs.inputs['Base Color'].default_value)
        info=tree.nodes.new('ShaderNodeObjectInfo')
        ramp=tree.nodes.new('ShaderNodeMapRange');ramp.name='Glass | varied roughness'
        ramp.inputs['To Min'].default_value=.09;ramp.inputs['To Max'].default_value=.30
        tree.links.new(info.outputs['Random'],ramp.inputs['Value'])
        tree.links.new(ramp.outputs[0],bs.inputs['Roughness'])
        mix=tree.nodes.new('ShaderNodeMixRGB');mix.name='Glass | varied tint'
        mix.inputs[1].default_value=tuple(c*.75 for c in base[:3])+(1,)
        mix.inputs[2].default_value=tuple(min(1,c*1.15+.025) for c in base[:3])+(1,)
        tree.links.new(info.outputs['Random'],mix.inputs[0]);tree.links.new(mix.outputs[0],bs.inputs['Base Color'])
    # Darkening at river level uses true world height, not per-mesh generated UVs.
    tree=g['foundation'].node_tree;bs=tree.nodes.get('Principled BSDF')
    geo=tree.nodes.new('ShaderNodeNewGeometry');sep=tree.nodes.new('ShaderNodeSeparateXYZ')
    ramp=tree.nodes.new('ShaderNodeMapRange');ramp.inputs['From Min'].default_value=0;ramp.inputs['From Max'].default_value=5
    mix=tree.nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.065,.10,.08,1);mix.inputs[2].default_value=(.30,.33,.32,1)
    tree.links.new(geo.outputs['Position'],sep.inputs[0]);tree.links.new(sep.outputs['Z'],ramp.inputs['Value']);tree.links.new(ramp.outputs[0],mix.inputs[0])
    existing=bs.inputs['Base Color'].links[0].from_socket
    patina=tree.nodes.new('ShaderNodeMixRGB');patina.name='Foundation | waterline times dirty joints'
    patina.blend_type='MULTIPLY';patina.inputs[0].default_value=1
    tree.links.new(existing,patina.inputs[1]);tree.links.new(mix.outputs[0],patina.inputs[2])
    tree.links.new(patina.outputs[0],bs.inputs['Base Color'])
    # Four spatial bases carry one travelling ripple along the shared world wind.
    # Signed key weights preserve wind direction; zero strength leaves Basis flat.
    from mathutils import Vector
    for ob in list(bpy.data.objects):
        if ob.type!='MESH':continue
        if ' flag |' in ob.name or ob.name.startswith('Sailing canvas'):
            ob.shape_key_add(name='Basis',from_mix=False)
            inverse=ob.matrix_world.to_3x3().inverted_safe()
            cloth_keys=[]
            xs=[v.co.x for v in ob.data.vertices]; xmin=min(xs); span=max(max(xs)-xmin,1e-6)
            if ' flag |' in ob.name:
                prefix=ob.name.split(' |')[0]
                xs=[v.co.x for other in bpy.data.objects if other.type=='MESH' and other.name.split(' |')[0]==prefix for v in other.data.vertices]
                xmin=min(xs);span=max(max(xs)-xmin,1e-6)
            for axis in range(2):
                direction=inverse@Vector((1 if axis==0 else 0,1 if axis==1 else 0,0))
                for quadrature in range(2):
                    key=ob.shape_key_add(name='Wind | %s %s'%('XY'[axis],['sine','cosine'][quadrature]),from_mix=False)
                    key.slider_min=-10;key.slider_max=10
                    for original,vertex in zip(ob.data.vertices,key.data):
                        x,y,z=original.co
                        pin=min(1,abs(x)/max(abs(min(xs)),abs(max(xs)),1e-6)) if ob.name.startswith('Sailing canvas') else (x-xmin)/span
                        phase=x*2+z*.7
                        wave=math.sin(phase) if quadrature==0 else math.cos(phase)
                        vertex.co+=direction*(1.8*pin*wave)
                    cloth_keys.append((axis,quadrature,key))
            for f in sorted(set([1,END]+list(range(1,END+1,max(1,round(FPS/6)))))):
                t=f/FPS;wind=wind_vector(t);phase=wind_time(t)*2.4
                for axis,quadrature,key in cloth_keys:
                    key.value=wind[axis]*(math.cos(phase) if quadrature==0 else math.sin(phase))
                    key.keyframe_insert('value',frame=f)
            ob['wind_source']='scene_components.wind.wind_vector / wind_time'
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
