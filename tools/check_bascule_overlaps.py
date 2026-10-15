"""Inspect labelled actual bascule/static triangle overlaps, without saving scene.

For acceptance: Blender --background --python this_file -- --clip --all
The --clip flag excludes only the first 1.3m local distance from each hinge.
"""
import bpy,json,sys,hashlib
from pathlib import Path
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1]
if '--all' in sys.argv:
    assert '--clip' in sys.argv and '--bound' not in sys.argv, 'Acceptance mode requires only the explicit 1.3m hinge exclusion'
bpy.ops.wm.open_mainfile(filepath=str(root/'Tower_Bridge/Tower_Bridge.blend'))
scene=bpy.context.scene
scene_sha256=hashlib.sha256((root/'Tower_Bridge/Tower_Bridge.blend').read_bytes()).hexdigest()
leaves=[o for o in scene.objects if o.type=='MESH' and o.parent and 'bascule hinge' in o.parent.name]
fixed=[o for o in scene.objects if o.type=='MESH' and o not in leaves and any(c.name[:2] in ('03','04','05','06','08','09') for c in o.users_collection)]
def clip(points,sign,bound):
    result=[]
    for a,b in zip(points,points[1:]+points[:1]):
        da=sign*a.x-bound;db=sign*b.x-bound
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):result.append(a+(b-a)*(da/(da-db)))
    return result

local_cache={}
group_cache={}
def local_geometry(ob,clip_enabled):
    clipped=clip_enabled and ob in leaves and '--clip' in sys.argv
    key=(ob.name,clipped)
    if key in local_cache:return local_cache[key]
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles()
    vertices=[];triangles=[];names=[]
    if not clipped:
        vertices=[v.co.copy() for v in m.vertices]
        for tri in m.loop_triangles:
            triangles.append(tuple(tri.vertices));names.append((ob.name,[tuple(vertices[i]) for i in tri.vertices]))
    else:
        bound=float(sys.argv[sys.argv.index('--bound')+1]) if '--bound' in sys.argv else 1.3
        sign=1 if ob.parent.name.startswith('North') else -1
        for tri in m.loop_triangles:
            points=clip([m.vertices[i].co.copy() for i in tri.vertices],sign,bound)
            if len(points)<3:continue
            offset=len(vertices);vertices.extend(points)
            for i in range(1,len(points)-1):
                triangles.append((offset,offset+i,offset+i+1));names.append((ob.name,[tuple(v) for v in points]))
    ev.to_mesh_clear()
    local_cache[key]=(vertices,triangles,names)
    return local_cache[key]

def tree(objects,clip_enabled=True):
    group_key=(tuple(ob.name for ob in objects),clip_enabled)
    if group_key not in group_cache:
        offset=0;tris=[];names=[];parts=[]
        for ob in objects:
            vertices,faces,labels=local_geometry(ob,clip_enabled)
            parts.append((ob,vertices))
            tris.extend(tuple(offset+i for i in face) for face in faces);names.extend(labels);offset+=len(vertices)
        group_cache[group_key]=(parts,tris,names)
    parts,tris,names=group_cache[group_key]
    vertices=[]
    for ob,local in parts:
        transform=ob.matrix_world.copy();vertices.extend(transform@v for v in local)
    return BVHTree.FromPolygons(vertices,tris,all_triangles=True,epsilon=0),names
scene.frame_set(1);static,labels=tree(fixed)
fixed_transforms=tuple(float(v) for ob in fixed for row in ob.matrix_world for v in row)
assert all(not ob.data.shape_keys and not ob.data.animation_data and not ob.animation_data for ob in fixed), 'Animated fixed geometry is unsupported'
assert all(not ob.data.animation_data and not ob.animation_data for ob in leaves), 'Animated leaf mesh/modifiers require per-frame geometry key'
report=[]
pose_cache={}
assert all(not ob.data.shape_keys for ob in leaves), 'Animated leaf geometry requires per-frame geometry evaluation'
frames=range(1,scene.frame_end+1) if '--all' in sys.argv else ([570,720] if '--bound' in sys.argv else [1,433,480,520,570,624,720,864,1000,1056,1440])
for f in frames:
    scene.frame_set(f);bpy.context.view_layer.update()
    assert tuple(float(v) for ob in fixed for row in ob.matrix_world for v in row)==fixed_transforms, 'Fixed bridge moves during collision validation'
    pose_key=tuple(float(v) for ob in leaves for row in ob.matrix_world for v in row)
    if pose_key in pose_cache:
        summary,hit_count=pose_cache[pose_key]
    else:
        moving,mlabels=tree(leaves);hits=moving.overlap(static)
        summary={}
        for a,b in hits:
            key=mlabels[a][0]+' VS '+labels[b][0]
            entry=summary.setdefault(key,{'count':0,'max_leaf_local_x':0.})
            entry['count']+=1;entry['max_leaf_local_x']=max(entry['max_leaf_local_x'],max(abs(v[0]) for v in mlabels[a][1]))
        north,nlabels=tree([o for o in leaves if o.parent.name.startswith('North')],clip_enabled=False)
        south,slabels=tree([o for o in leaves if o.parent.name.startswith('South')],clip_enabled=False)
        mutual=north.overlap(south)
        for a,b in mutual:
            key='MUTUAL '+nlabels[a][0]+' VS '+slabels[b][0]
            entry=summary.setdefault(key,{'count':0,'max_leaf_local_x':0.})
            entry['count']+=1;entry['max_leaf_local_x']=max(entry['max_leaf_local_x'],max(abs(v[0]) for v in nlabels[a][1]))
        hit_count=len(hits)+len(mutual);pose_cache[pose_key]=(summary,hit_count)
    report.append({'frame':f,'pairs':summary})
    if '--all' in sys.argv and f%120==0:print('BASCULE_FRAME',f,'overlaps',hit_count,'unique_states',len(pose_cache),flush=True)
assert hashlib.sha256((root/'Tower_Bridge/Tower_Bridge.blend').read_bytes()).hexdigest()==scene_sha256, 'Primary scene file changed during validation'
if '--all' in sys.argv:
    full={'scene_sha256':scene_sha256,'passed':not any(item['pairs'] for item in report),'frames_checked':len(report),'unique_geometry_states':len(pose_cache),'cache_contract':'Exact unrounded float world matrices; evaluated leaf geometry has no shape keys or animated modifiers; fixed bridge meshes and transforms unchanged',
        'scope':'Evaluated leaf mesh triangles versus evaluated fixed bridge tower, arch, deck, suspension and furniture meshes at every integer frame; triangle clipping excludes only first 1.3m of leaf local X from hinge, representing mechanical joint. Opposite leaf versus leaf uses all evaluated triangles without hinge or centre-tip exclusions. Triangle BVH overlap at zero epsilon; touching/coplanar contacts may be reported; no swept subframe proof.',
        'violating_frames':[item for item in report if item['pairs']],
        'fixed_mesh_objects':len(fixed),'moving_leaf_mesh_objects':len(leaves)}
    (root/'Tower_Bridge/bascule_validation.json').write_text(json.dumps(full,indent=2))
    print('BASCULE_VALIDATION',json.dumps({k:v for k,v in full.items() if k!='violating_frames'}),flush=True)
    if full['violating_frames']:
        print('BASCULE_FIRST_FAILURE',json.dumps(full['violating_frames'][0]),flush=True)
        raise RuntimeError('Bascule intersects fixed bridge outside the explicit hinge joint')
else:print('JOINT_DIAGNOSTIC',json.dumps(report),flush=True)
(root/('research/bascule-overlap-clipped-'+sys.argv[sys.argv.index('--bound')+1]+'.json' if '--bound' in sys.argv else 'research/bascule-overlap-clipped.json' if '--clip' in sys.argv else 'research/bascule-overlap-diagnostic.json')).write_text(json.dumps(report,indent=2))
