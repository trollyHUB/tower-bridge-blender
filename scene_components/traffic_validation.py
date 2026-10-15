"""Inspect actual evaluated Blender geometry and baked traffic animation."""
import math

from .scenario import reference_frame
from .traffic import barrier_angle, signal_state, vehicle_specs, longitudinal_position


def validate(scene):
    import bpy
    from mathutils import Vector

    actors = [o for o in scene.objects if o.get('actor_type') == 'vehicle']
    gates = [o for o in scene.objects if o.get('actor_type') == 'barrier']
    assert len(actors) == 14, ('vehicle count', len(actors))
    assert {o['vehicle_type'] for o in actors} == {'bus', 'taxi', 'car', 'truck'}
    assert len(gates) == 2, ('barrier count', len(gates))
    meshes = {actor: [o for o in actor.children_recursive if o.type == 'MESH'] for actor in actors}
    wheels = {actor: [o for o in actor.children if o.get('actor_type') == 'wheel'] for actor in actors}
    assert all(meshes.values()), 'Missing actual vehicle meshes'
    assert all(len(w) == 4 for w in wheels.values()), 'Every vehicle needs four wheels'
    last_frame = scene.frame_current
    previous = {}
    recycled = set()
    minimum_gap = math.inf
    worst_wheel_error = 0.0
    closest_stop_front = -math.inf
    checked = 0
    try:
        for frame in range(scene.frame_start, scene.frame_end+1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            ref = reference_frame(frame)
            bounds = []
            for actor in actors:
                direction = int(actor['direction'])
                position = actor.matrix_world.translation.x
                angles = [w.rotation_euler.y for w in wheels[actor]]
                if actor in previous:
                    old_x, old_angles, old_odometer = previous[actor]
                    distance = float(actor['odometer'])-old_odometer
                    assert distance >= -1e-4, ('vehicle reverses', frame, actor.name)
                    if direction*(position-old_x) < -1:
                        # Low-fps output can skip the portal frames. Inspect each
                        # reference-timeline solver step between output samples;
                        # require the complete body inside both portals at wrap.
                        spec=next(item for item in vehicle_specs() if item['name']==actor.name)
                        first=max(1,math.floor(reference_frame(frame-1)))
                        last=math.ceil(ref)
                        wraps=[]
                        for tick in range(first+1,last+1):
                            before=longitudinal_position(spec,tick-1)
                            after=longitudinal_position(spec,tick)
                            if after<before-1:
                                wraps.append((before,after))
                        assert wraps, ('unexplained vehicle teleport',frame,actor.name)
                        assert all(abs(before)-actor['length']/2>199 and abs(after)-actor['length']/2>199 for before,after in wraps), ('visible recycle',frame,actor.name,wraps)
                        recycled.add(actor)
                    for wheel, angle, old_angle in zip(wheels[actor], angles, old_angles):
                        error = abs((angle-old_angle)*wheel['wheel_radius']-distance)
                        worst_wheel_error = max(worst_wheel_error, error)
                        assert error < .002, ('wheel slip', frame, wheel.name, error)
                previous[actor] = (position, angles, float(actor['odometer']))
                if actor.scale.x < .5:
                    continue  # Hidden beyond the road-end portals.
                points = []
                for mesh in meshes[actor]:
                    evaluated = mesh.evaluated_get(graph)
                    points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
                xmin, xmax = min(p.x for p in points), max(p.x for p in points)
                ymin, ymax = min(p.y for p in points), max(p.y for p in points)
                assert xmin > -219.1 and xmax < 219.1, ('vehicle escapes covered portal',frame,actor.name,xmin,xmax)
                bounds.append((actor, xmin, xmax, ymin, ymax))
                front = xmax if direction == 1 else -xmin
                if (actor['schedule_mode'] == 'queue' or actor in recycled) and 193 <= ref < 1105:
                    closest_stop_front = max(closest_stop_front, front)
                    assert front <= -abs(actor['stop_line']), ('front crosses stop line', frame, actor.name, front)
                if 337 <= ref < 1105:
                    assert xmax <= -30.5 or xmin >= 30.5, ('vehicle in moving span', frame, actor.name)
                    for gate in gates:
                        gx = gate.matrix_world.translation.x
                        assert xmax < gx-.15 or xmin > gx+.15, ('vehicle intersects barrier', frame, actor.name)
            for i, a in enumerate(bounds):
                for b in bounds[i+1:]:
                    if min(a[4], b[4])-max(a[3], b[3]) <= 0:
                        continue
                    gap = max(a[1]-b[2], b[1]-a[2])
                    minimum_gap = min(minimum_gap, gap)
                    assert gap > 0, ('actual body collision', frame, a[0].name, b[0].name)
            for gate in gates:
                angle = abs(gate.rotation_euler.x)
                assert abs(angle-barrier_angle(ref)) < .0002, ('barrier schedule', frame, gate.name)
                if 433 <= ref <= 1056:
                    assert angle < .0002, ('barrier open during lift', frame, gate.name)
            for direction in (-1, 1):
                for state in ('green', 'red'):
                    mat = bpy.data.materials[f'Signal {direction:+d} {state}']
                    strength = mat.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value
                    assert (strength > 4) == (state == signal_state(ref)), ('signal interlock', frame, direction, state)
            checked += 1
    finally:
        scene.frame_set(last_frame)
    return {'passed': True, 'frames_checked': checked, 'vehicle_count': len(actors),
            'vehicle_types': sorted({o['vehicle_type'] for o in actors}),
            'minimum_actual_body_gap_m': minimum_gap,
            'closest_queued_front_direction_coordinate_m': closest_stop_front,
            'maximum_wheel_distance_error_m': worst_wheel_error,
            'checks': ['evaluated_mesh_bounds', 'full_body_span_clearance', 'stop_lines',
                       'barrier_intersections', 'barrier_timing', 'signal_interlock',
                       'wheel_distance', 'no_reverse', 'hidden_portal_recycling']}
