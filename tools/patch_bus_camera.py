"""Narrow, fail-closed camera correction. May run during an old render only after verifying its identity is fixed once at startup.

blender -b --threads 2 --python tools/patch_bus_camera.py -- --probe
blender -b --threads 2 --python tools/patch_bus_camera.py -- --apply
The exhaustive RNA comparison intentionally fails on inaccessible properties.
"""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scene_components.render_manifest import sha, make_identity
CAMERA='09 | Bus stop camera'
SKIP={'rna_type','id_data','original','evaluated_get','session_uid','is_updated','is_updated_data','is_updated_transform','tag','users','is_evaluated','is_runtime_data','depsgraph'}
# UI-only datablocks are deliberately outside the render dependency graph.
UI={'screens','window_managers','workspaces','all_ids'}  # all_ids duplicates every collection, including UI
DERIVED_MESH={'MeshVertex':{'normal','undeformed_co'},'MeshPolygon':{'normal','center','area'},'MeshLoop':{'normal','tangent','bitangent','bitangent_sign'},'Mesh':{'vertex_normals','polygon_normals','corner_normals','loop_triangles'}}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def custom_keys(value):
    try:return sorted(value.keys())
    except TypeError:return []  # RNA explicitly reports IDProperties unsupported

def encode(value,seen,path):
    if value is None or isinstance(value,(bool,str,int,float)):
        if isinstance(value,float) and not math.isfinite(value):return {'nonfinite':str(value)}
        return value
    if isinstance(value,bpy.types.ID) and not value.is_embedded_data:
        return {'id_type':value.bl_rna.identifier,'id_name':value.name_full}
    if isinstance(value,bpy.types.bpy_prop_array):
        return [encode(v,seen,path+'/'+str(i)) for i,v in enumerate(value)]
    if isinstance(value,bpy.types.bpy_prop_collection):
        metadata={}
        if hasattr(value,'bl_rna'):
            for prop in value.bl_rna.properties:
                key=prop.identifier
                if key in SKIP:continue
                metadata[key]=encode(getattr(value,key),seen,path+'/metadata/'+key)
        first=next(iter(value),None)
        if first is not None and hasattr(first,'bl_rna') and not isinstance(first,bpy.types.ID):
            props=[p for p in first.bl_rna.properties if p.identifier not in SKIP and p.identifier not in DERIVED_MESH.get(first.bl_rna.identifier,set())]
            # Exact C-level bulk reads for leaf data such as mesh vertices,
            # topology, color/UV attributes and curve keyframe coordinates.
            if all(p.type in ('BOOLEAN','INT','FLOAT','STRING','ENUM') for p in props):
                fields={}
                for prop in props:
                    key=prop.identifier
                    if prop.type in ('BOOLEAN','INT','FLOAT'):
                        code={'BOOLEAN':'b','INT':'i','FLOAT':'f'}[prop.type]
                        count=len(value)*(prop.array_length if prop.is_array else 1)
                        buffer=array.array(code,[0])*count
                        try:
                            if (prop.is_array and prop.array_length==0) or (first.bl_rna.identifier=='MeshPolygon' and key=='vertices'):raise TypeError('Variable length array')
                            value.foreach_get(key,buffer)
                        except (RuntimeError,TypeError):
                            fields[key]=[encode(getattr(v,key),seen,path+'/'+str(i)+'/'+key) for i,v in enumerate(value)]
                        else:fields[key]={'type':code,'length':count,'bytes_sha256':hashlib.sha256(buffer.tobytes()).hexdigest()}
                    else:fields[key]=[getattr(v,key) for v in value]
                return {'count':len(value),'fields':fields,'metadata':metadata}
        return {'items':[encode(v,seen,path+'/'+str(i)) for i,v in enumerate(value)],'metadata':metadata}
    if hasattr(value,'bl_rna'):
        pointer=value.as_pointer()
        if pointer in seen:return {'ref':seen[pointer]}
        seen[pointer]=path
        data={}
        for prop in value.bl_rna.properties:
            key=prop.identifier
            if key in SKIP or key in DERIVED_MESH.get(value.bl_rna.identifier,set()) or (isinstance(value,bpy.types.Attribute) and key=='storage_type'):continue
            # Runtime caches have no saved input meaning and can change on save.
            try:data[key]=encode(getattr(value,key),seen,path+'/'+key)
            except Exception as exc:raise RuntimeError(f'Uncovered RNA property {path}/{key}: {exc}') from exc
        if hasattr(value,'keys'):
            data['custom_properties']={key:encode(value[key],seen,path+'/custom/'+key) for key in custom_keys(value)}
        return data
    if hasattr(value,'to_list'):return encode(value.to_list(),seen,path)
    if hasattr(value,'items') and not hasattr(value,'bl_rna'):
        return {str(k):encode(v,seen,path+'/'+str(k)) for k,v in value.items()}
    try:return [encode(v,seen,path+'/'+str(i)) for i,v in enumerate(value)]
    except TypeError as exc:raise TypeError(f'Unsupported render dependency {path}: {type(value)}') from exc

def snapshot():
    """Hash every saved datablock and nested RNA, without coordinate rounding."""
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    result={}
    for prop in bpy.data.bl_rna.properties:
        name=prop.identifier
        if prop.type!='COLLECTION' or name in UI:continue
        items=getattr(bpy.data,name)
        entries={}
        for item in sorted(items,key=lambda i:i.name_full):
            # Encode the root ID as a structure; pointers to IDs remain names.
            data={}
            seen={item.as_pointer():'/'+name+'/'+item.name_full}
            for field in item.bl_rna.properties:
                key=field.identifier
                if key in SKIP or key in DERIVED_MESH.get(item.bl_rna.identifier,set()):continue
                try:data[key]=encode(getattr(item,key),seen,'/'+name+'/'+item.name_full+'/'+key)
                except Exception as exc:raise RuntimeError(f'Uncovered ID {name}/{item.name_full}/{key}: {exc}') from exc
            data['custom_properties']={k:encode(item[k],seen,'/custom/'+k) for k in sorted(item.keys())}
            entries[item.name_full]=digest(data)
        result[name]=entries
        print("FINGERPRINT_COLLECTION",name,len(entries),flush=True)
    return result

def transform(cam):
    return {'location':list(cam.location),'rotation_euler':list(cam.rotation_euler),'ortho_scale':cam.data.ortho_scale}

def restore(cam,state):
    cam.location=state['location'];cam.rotation_euler=state['rotation_euler'];cam.data.ortho_scale=state['ortho_scale']
    bpy.context.view_layer.update()

def normalized_snapshot(cam,old):
    new=transform(cam)
    restore(cam,old)
    result=snapshot()
    restore(cam,new)
    return result

def assert_no_dependents(cam):
    assert cam.type=='CAMERA' and cam.data.type=='ORTHO'
    assert not cam.animation_data and not cam.data.animation_data and not cam.constraints
    assert not cam.parent and not cam.children and len([o for o in bpy.data.objects if o.data==cam.data])==1
    assert not bpy.data.armatures,'Armature constraint dependencies require separate certification'
    assert not any(m.has_custom_normals for m in bpy.data.meshes),'Custom normals require separate certification'
    assert not bpy.data.libraries,'External linked dependencies cannot be certified'
    for ob in bpy.data.objects:
        for constraint in list(ob.constraints)+list(ob.modifiers):
            for prop in constraint.bl_rna.properties:
                if prop.type=='POINTER':
                    assert getattr(constraint,prop.identifier,None)!=cam,'Camera referenced by constraint'
    for prop in bpy.data.bl_rna.properties:
        if prop.type!='COLLECTION':continue
        for item in getattr(bpy.data,prop.identifier):
            animation=getattr(item,'animation_data',None)
            if animation:
                for driver in animation.drivers:
                    assert 'bpy' not in driver.driver.expression,'Arbitrary bpy driver dependency cannot be certified'
                    for variable in driver.driver.variables:
                        for target in variable.targets:
                            assert target.id not in (cam,cam.data),'Camera referenced by driver'
    # Camera-dependent compositing/geometry nodes are excluded conservatively.
    groups=list(bpy.data.node_groups)+[m.node_tree for m in bpy.data.materials if m.node_tree]+[w.node_tree for w in bpy.data.worlds if w.node_tree]+[getattr(s,'compositing_node_group',None) for s in bpy.data.scenes if getattr(s,'compositing_node_group',None)]
    for group in groups:
        for node in group.nodes:
            for prop in node.bl_rna.properties:
                if prop.type=='POINTER':
                    value=getattr(node,prop.identifier,None)
                    if isinstance(value,bpy.types.ID):assert value not in (cam,cam.data),'Camera referenced by shader/node'
            for socket in node.inputs:
                value=getattr(socket,'default_value',None)
                if isinstance(value,bpy.types.ID):assert value not in (cam,cam.data)

def affected_frames(scene,cam):
    markers=sorted((m.frame,m.name,m.camera) for m in scene.timeline_markers if m.camera)
    result=[]
    active=scene.camera
    for f in range(scene.frame_start,scene.frame_end+1):
        for tick,name,camera in markers:
            if tick>f:break
            active=camera
        if active==cam:result.append(f)
    assert result and result==list(range(min(result),max(result)+1))
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--probe',action='store_true');parser.add_argument('--audit',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    assert sum((args.apply,args.probe,args.audit))==1,'Choose --apply, --probe or --audit'
    source=ROOT/'Tower_Bridge/Tower_Bridge.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene;cam=bpy.data.objects[CAMERA]
    old=transform(cam);assert_no_dependents(cam)
    saved_frame=scene.frame_current;saved_camera=scene.camera
    assert not [i for i in bpy.data.images if i.source=='FILE' and not i.packed_file], 'Unpacked external images cannot be certified'
    assert not bpy.data.cache_files and not bpy.data.volumes, 'External simulation/volume data cannot be certified'
    assert not [f for f in bpy.data.fonts if f.filepath!='<builtin>' and not f.packed_file], 'External fonts cannot be certified'
    before=snapshot() if args.apply or args.audit else None
    cam.location=(162,18,21);cam.rotation_euler=(Vector((157,4,12))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=23
    new=transform(cam)
    if args.probe:
        scene.frame_set(378);scene.camera=cam;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=True
        scene.render.resolution_x=320;scene.render.resolution_y=180;scene.render.resolution_percentage=100
        scene.render.filepath=str(ROOT/'research/bus_camera_probe.png');bpy.ops.render.render(write_still=True)
        print('PROBE_ONLY_NO_SAVE',scene.render.filepath);return
    after=normalized_snapshot(cam,old)
    differing=[(kind,name) for kind in before for name in before[kind] if before[kind][name]!=after.get(kind,{}).get(name)]
    assert after==before,('Unexpected in-memory render dependency change',differing)
    frames=affected_frames(scene,cam)
    if args.audit:
        print('READ_ONLY_AUDIT_OK',digest(before),min(frames),max(frames),flush=True);return
    archive=ROOT/'research/before_bus_camera_fix';archive.mkdir(parents=True,exist_ok=True)
    backup=archive/source.name
    assert not backup.exists(),'Refusing to replace camera baseline backup'
    shutil.copy2(source,backup)
    identity=make_identity(source,ROOT/'config/scene.json',ROOT/'render_tower_bridge.py','final',bpy.app.version_string)
    identity['manifest_implementation_sha256']=sha(ROOT/'scene_components/render_manifest.py')
    scene.frame_set(saved_frame);scene.camera=saved_camera
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(source))
        bpy.ops.wm.open_mainfile(filepath=str(source));cam=bpy.data.objects[CAMERA]
        assert transform(cam)==new,'Camera patch did not persist exactly'
        assert normalized_snapshot(cam,old)==before,'Saved render dependency changed beyond camera correction'
    except Exception:
        shutil.copy2(backup,source)  # Failed certification restores original bytes.
        raise
    report={'passed':True,'old_scene_sha256':sha(backup),'new_scene_sha256':sha(source),'identity_before':identity,
            'old_camera':old,'new_camera':new,'camera':CAMERA,'affected_frames':frames,
            'normalized_datablocks':before,'normalized_fingerprint_sha256':digest(before),
            'patch_implementation_sha256':sha(__file__),
            'scope':'Both snapshots evaluated at frame1; initial saved frame and camera restored before save. Exact exhaustive saved RNA properties of all datablocks except UI screens/workspaces/window managers, with only camera location, Euler rotation and orthographic scale normalized to baseline. Derived attribute storage representation and mesh normals/areas/tessellation excluded (custom normals rejected), as are runtime flags/users/session IDs/evaluated depsgraph; unsupported values fail closed. Includes mesh/topology/attributes, node graphs, lights, actions/drivers, render settings and markers.'}
    (archive/'proof.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('CAMERA_PATCH_PROOF',str(archive/'proof.json'),min(frames),max(frames),flush=True)

if __name__=='__main__':main()

