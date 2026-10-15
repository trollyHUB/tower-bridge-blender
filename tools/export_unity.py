"""Run with Blender: blender -b Tower_Bridge/Tower_Bridge.blend -P tools/export_unity.py.

Evaluated geometry is baked in metres into Unity axes (x,z,y). No Blender importer,
FBX SDK, asset store content or network package is required by the Unity project.
"""
import json
import pathlib
import struct
import hashlib


def unity_point(v):
    return (v[0], v[2], v[1])


def export():
    import bpy
    from mathutils import Matrix
    out = pathlib.Path(__file__).resolve().parents[1] / 'Unity/Assets/StreamingAssets'
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.frame_set(1)
    deps = bpy.context.evaluated_depsgraph_get()
    roots = [o for o in scene.objects if o.get('actor_type') or 'bascule hinge' in o.name]
    # Hidden recycled vehicles use zero root scale. Recover their local geometry
    # before evaluating meshes; animation samples below restore source visibility.
    for root in roots:
        if abs(root.matrix_world.determinant()) < 1e-10:
            root.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    groups = {'Static': {}}
    root_by_name = {o.name: o for o in roots}
    for root in roots:
        groups[root.name] = {}
    materials = []
    mat_ids = {}
    for obj in scene.objects:
        if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT'} or obj.hide_render:
            continue
        root = next((p for p in [obj, *ancestors(obj)] if p in roots), None)
        group = groups[root.name if root else 'Static']
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        if mesh is None:
            continue
        mesh.calc_loop_triangles()
        transform = (root.matrix_world.inverted_safe() if root else Matrix.Identity(4)) @ obj.matrix_world
        for tri in mesh.loop_triangles:
            mat = obj.material_slots[tri.material_index].material if tri.material_index < len(obj.material_slots) else None
            key = mat.name if mat else 'Default'
            if key not in mat_ids:
                color = list(mat.diffuse_color) if mat else [.55, .55, .55, 1]
                if mat and mat.use_nodes:
                    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                    if bsdf:
                        color = list(bsdf.inputs['Base Color'].default_value)
                mat_ids[key] = len(materials)
                materials.append({'name': key, 'color': color})
            bucket = group.setdefault(mat_ids[key], [])
            # Axis swap has negative determinant: reverse winding.
            for idx in reversed(tri.vertices):
                bucket.append(unity_point(transform @ mesh.vertices[idx].co))
        evaluated.to_mesh_clear()
    manifest = {'format': 1, 'units': 'metres', 'axis_mapping': 'Blender XYZ -> Unity XZY; winding reversed',
                'source_sha256': hashlib.sha256(pathlib.Path(bpy.data.filepath).read_bytes()).hexdigest(),
                'fps': scene.render.fps, 'end_frame': scene.frame_end, 'materials': materials, 'groups': []}
    with (out / 'scene.bin').open('wb') as stream:
        for name, buckets in groups.items():
            root = root_by_name.get(name)
            item = {'name': name, 'actor_type': str(root.get('actor_type', 'hinge')) if root else 'static', 'parts': [], 'samples': []}
            for material, vertices in buckets.items():
                for start in range(0, len(vertices), 60000):
                    chunk = vertices[start:start + 60000]
                    item['parts'].append({'material': material, 'offset': stream.tell(), 'count': len(chunk)})
                    stream.write(struct.pack('<' + 'f' * len(chunk)*3, *(c for v in chunk for c in v)))
            manifest['groups'].append(item)
    swap = Matrix(((1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1)))
    # Every source frame, including articulated root transforms, is preserved.
    for frame in range(1, scene.frame_end + 1):
        scene.frame_set(frame)
        for item in manifest['groups'][1:]:
            root = root_by_name[item['name']]
            loc, rot, scale = (swap @ root.matrix_world @ swap).decompose()
            item['samples'].append({'p': list(loc), 'q': [rot.x,rot.y,rot.z,rot.w], 's': list(scale)})
    (out / 'scene.json').write_text(json.dumps(manifest, separators=(',', ':')), encoding='utf-8')
    print('UNITY_EXPORT', len(groups), 'groups', sum(len(p['samples']) for p in manifest['groups']), 'transform samples', flush=True)


def ancestors(obj):
    result = []
    while obj.parent:
        obj = obj.parent
        result.append(obj)
    return result


if __name__ == '__main__':
    export()
