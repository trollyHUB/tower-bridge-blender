"""Geometry checks for the generated city, walkers and river vessels.

BVH checks detect triangle surface intersections at the stated sample frames;
they are not a continuous swept-volume or minimum-distance proof.
"""
import math
from .scenario import reference_frame, CONFIG


def validate(scene):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    def descendants(root, skip_wakes=False):
        result = []
        for ob in root.children_recursive:
            if ob.type != 'MESH':
                continue
            parent = ob.parent
            wake = False
            while parent and parent != root:
                wake |= 'wake' in parent.name.lower()
                parent = parent.parent
            if not (skip_wakes and wake):
                result.append(ob)
        return result

    def bounds(objects):
        pts = [ob.matrix_world @ Vector(v) for ob in objects for v in ob.bound_box]
        assert pts, 'Missing mesh geometry'
        return tuple((min(p[k] for p in pts), max(p[k] for p in pts)) for k in range(3))

    def overlapping(a, b, epsilon=0):
        return all(min(a[k][1], b[k][1])-max(a[k][0], b[k][0]) > epsilon for k in range(3))

    def surface(objects, above=None):
        vertices, triangles = [], []
        for ob in objects:
            evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = evaluated.to_mesh()
            mesh.calc_loop_triangles()
            offset = len(vertices)
            world = [evaluated.matrix_world @ v.co for v in mesh.vertices]
            vertices.extend(world)
            for tri in mesh.loop_triangles:
                ids = tuple(tri.vertices)
                if above is None or max(world[i].z for i in ids) > above:
                    triangles.append(tuple(offset+i for i in ids))
            evaluated.to_mesh_clear()
        if not triangles:
            return None
        return BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=.00001)

    walkers = [o for o in scene.objects if o.name.startswith('Walker ') and o.get('route')]
    people = [o for o in scene.objects if o.get('actor_type') == 'person']
    cars = [o for o in scene.objects if o.get('actor_type') == 'vehicle']
    sail = next(o for o in scene.objects if o.get('actor_type') == 'sailboat')
    launch = next(o for o in scene.objects if o.get('actor_type') == 'launch')
    leaves = [o for o in scene.objects if o.type == 'MESH' and o.parent and 'bascule hinge' in o.parent.name]
    walkways = [o for o in scene.objects if o.type == 'MESH' and
                any(c.name == '05 | High-level walkways' for c in o.users_collection)]
    assert len(walkers) == max(0,min(12,int(CONFIG.get('people',{}).get('bank_walkers',8))))+2, ('pedestrian count', len(walkers))
    assert leaves, 'Missing bascule meshes'
    assert walkways, 'Missing fixed upper walkways'
    walkway_low = bounds(walkways)[2][0]
    walker_mesh = {o: descendants(o) for o in people}
    car_mesh = {o: descendants(o) for o in cars}
    sail_mesh, launch_mesh = descendants(sail, True), descendants(launch, True)
    names = ['RIVERSIDE STORES', 'THE BRIDGE HOTEL', 'THAMES CAFE', 'ALBERT TERRACE',
             'BUTLERS WHARF', 'RIVER WORKSHOPS', 'ST KATHARINE HOUSE', 'DOCKSIDE GALLERY']
    buildings = {name: [o for o in scene.objects if o.type == 'MESH' and o.name.startswith(name+' |')]
                 for name in names}
    assert all(buildings.values()), 'Missing one of the eight building groups'
    for name, objects in buildings.items():
        bb = bounds(objects)
        assert bb[0][1] < -110 or bb[0][0] > 110, ('building enters river corridor', name)
        assert bb[1][1] < -5.7 or bb[1][0] > 5.7, ('building enters roadway', name)
        assert bb[2][0] >= 10.1, ('building sinks below bank', name, bb[2][0])

    original = scene.frame_current
    scene.frame_set(1)
    bpy.context.view_layer.update()
    # Static meshes contain multiple disconnected fixtures. Triangle BVH tests
    # are required here; their whole-object AABBs would give false collisions.
    static = [o for o in scene.objects if o.type == 'MESH' and not o.parent and
              any(c.name in ('City | buildings', 'City | streets', 'City | gardens', 'City | furniture') for c in o.users_collection)]
    obstacles = [(o.name, bounds([o]), surface([o], above=10.55)) for o in static]
    obstacles = [item for item in obstacles if item[2] is not None]
    samples = set(range(scene.frame_start, scene.frame_end+1, 12))
    for ref in (1, 192, 193, 320, 336, 337, 432, 433, 624, 625, 720, 864, 865, 1056, 1057, 1104, 1105, 1440):
        samples.add(max(1, min(scene.frame_end, round(ref*scene.frame_end/1440))))
    min_launch_clearance = math.inf
    min_waiting_sail_distance = math.inf
    min_walkway_margin = math.inf
    pedestrian_frames = 0
    vessel_samples = 0
    obstacle_queries = 0
    snapshots = {}

    def state():
        objects = people+[sail, launch]
        return tuple(tuple(float(v) for row in o.matrix_world for v in row) for o in objects)

    try:
        for frame in range(scene.frame_start, scene.frame_end+1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            ref = reference_frame(frame)
            traffic = [(o, bounds(car_mesh[o])) for o in cars if o.scale.x >= .5]
            for walker in people:
                bb = bounds(walker_mesh[walker])
                if 'bank promenade' in walker.get('route',''):
                    # Entire body stays on a bank, outside its street and away
                    # from the river edge; tests use geometry, not its origin.
                    assert bb[0][1] < -110.5 or bb[0][0] > 110.5, ('walker leaves bank', frame, walker.name)
                    assert bb[0][0] > -210 and bb[0][1] < 210
                    assert bb[1][0] > -68 and bb[1][1] < 68
                    assert bb[1][1] < -8 or bb[1][0] > 8, ('bank walker enters road', frame, walker.name)
                if walker.get('role')=='walker' and 337 <= ref < 1105:
                    assert bb[0][1] < -30.5 or bb[0][0] > 30.5, ('walker on moving leaf during closure', frame, walker.name)
                for car, cb in traffic:
                    assert not overlapping(bb, cb), ('walker/vehicle bounds overlap', frame, walker.name, car.name)
                near = [(name, tree) for name, obb, tree in obstacles if overlapping(bb, obb)]
                if near:
                    tree = surface(walker_mesh[walker])
                    for name, obstacle in near:
                        obstacle_queries += 1
                        assert not tree.overlap(obstacle), ('walker/static surface intersection', frame, walker.name, name)
            pedestrian_frames += 1
            sb, lb = bounds(sail_mesh), bounds(launch_mesh)
            assert not overlapping(sb, lb), ('vessel bounds overlap', frame)
            for vessel, vb in ((sail, sb), (launch, lb)):
                assert vb[0][0] > -109 and vb[0][1] < 109, ('vessel enters quay wall', frame, vessel.name)
                margin = walkway_low-vb[2][1]
                min_walkway_margin = min(min_walkway_margin, margin)
                assert margin > 0, ('vessel above fixed walkway underside', frame, vessel.name)
            # The low launch remains below even the lowest point of the closed
            # structural envelope. This is a conservative vertical bound.
            if ref <= 432 or ref >= 1056:
                deck_low = bounds(leaves)[2][0]
                clearance = deck_low-lb[2][1]
                min_launch_clearance = min(min_launch_clearance, clearance)
                assert clearance > 0, ('launch taller than closed deck envelope', frame, clearance)
            if ref < 625:
                distance = -8-sb[1][1]
                min_waiting_sail_distance = min(min_waiting_sail_distance, distance)
                assert distance > 0, ('waiting sailboat enters bridge channel early', frame, sb[1])
            if ref >= 865:
                assert sb[1][0] > 8, ('sailboat not fully clear before lowering', frame, sb[1])
            if frame in samples:
                leaf_bounds = bounds(leaves)
                for vessel, meshes, vb in ((sail, sail_mesh, sb), (launch, launch_mesh, lb)):
                    if overlapping(vb, leaf_bounds):
                        vtree = surface(meshes)
                        ltree = surface(leaves)
                        assert not vtree.overlap(ltree), ('vessel/bascule surface intersection', frame, vessel.name)
                vessel_samples += 1
                snapshots[frame] = state()
        # Seek in reverse and irregular order to expose history-dependent
        # handlers or simulations. Compare the actual evaluated world matrices.
        seek_frames = sorted(snapshots)[::max(1, len(snapshots)//17)]
        seek_frames = seek_frames[::-1]+seek_frames[::2]+seek_frames[1::2]
        max_seek_error = 0.0
        for frame in seek_frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            fresh = state()
            error = max(abs(a-b) for old, new in zip(snapshots[frame], fresh) for a, b in zip(old, new))
            max_seek_error = max(max_seek_error, error)
            assert error < .00001, ('direct seek changes actor state', frame, error)
    finally:
        scene.frame_set(original)
    return {'passed': True, 'pedestrian_count': len(people), 'walking_pedestrian_count':len(walkers), 'stationary_people_count':len(people)-len(walkers),
            'person_vehicle_scope':'Every frame, complete descendant mesh world AABBs for all walking and stationary people versus all visible cars', 'pedestrian_frames_checked': pedestrian_frames,
            'building_groups_checked': len(buildings), 'static_obstacle_bvh_queries': obstacle_queries,
            'static_obstacle_scope': 'All people versus unparented city building, street, garden and furniture mesh triangles above 10.55m; cafe-owned parented chairs excluded; AABB broad phase then triangle BVH overlap; no penetration-depth or swept-volume proof',
            'vessel_surface_sample_count': vessel_samples, 'vessel_surface_sample_frames': sorted(samples),
            'vessel_surface_test_scope': 'World-space triangle intersections with moving leaves; sampled every 12 frames and phase boundaries',
            'minimum_launch_closed_deck_vertical_margin_m': min_launch_clearance,
            'minimum_waiting_sailboat_channel_distance_m': min_waiting_sail_distance,
            'minimum_vessel_fixed_walkway_vertical_margin_m': min_walkway_margin,
            'direct_seek_checks': len(seek_frames), 'maximum_direct_seek_matrix_error': max_seek_error}
