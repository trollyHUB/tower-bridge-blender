"""Deterministic, baked traffic for the 60 second bridge demonstration.

The schedule functions intentionally have no Blender dependency, allowing full
body clearance and spacing checks outside Blender. Coordinates are metres.
"""
import math

FPS = 24
LAST_FRAME = 1440
STOP_LINE = 55.0
ROAD_Z = 10.2
VEHICLE_TYPES = {
    'bus': (10.8, 2.35, 4.25),
    'taxi': (4.7, 1.85, 1.7),
    'car': (4.4, 1.8, 1.55),
    'truck': (7.8, 2.3, 3.15),
}


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3.0-2.0*t)


def signal_state(frame):
    return 'green' if frame < 193 or frame >= 1105 else 'red'


def barrier_angle(frame):
    """Zero is closed; pi/2 is raised. Closing ends before leaf motion."""
    if frame <= 336:
        return math.pi/2
    if frame <= 432:
        return math.pi/2*(1-smoothstep((frame-337)/95))
    if frame <= 1056:
        return 0.0
    return math.pi/2*smoothstep((frame-1057)/47)


def vehicle_specs():
    specs = []
    for direction in (1, -1):
        # These vehicles have already committed before the warning. All their
        # trailing edges clear the moving span well before frame 336.
        for i, kind in enumerate(('taxi', 'bus', 'car')):
            specs.append(dict(name=f'Traffic initial {direction:+d} {kind}',
                              kind=kind, direction=direction, mode='through',
                              start=-40.0-i*50.0))
        # Front bumper of the leader stops 1.5 m before the painted line.
        front = -_settings().get('stop_line',55)-1.5
        for i, kind in enumerate(('truck', 'taxi', 'car', 'bus')):
            length = VEHICLE_TYPES[kind][0]
            target = front-length/2
            specs.append(dict(name=f'Traffic queue {direction:+d} {i+1} {kind}',
                              kind=kind, direction=direction, mode='queue',
                              start=target-150.0, target=target, index=i))
            front -= length+_settings().get('minimum_gap',4.0)
    return specs


def _settings():
    from .scenario import CONFIG
    return CONFIG.get('traffic', {})


from functools import lru_cache


@lru_cache(maxsize=16)
def _schedule(speed, gap, stop_line, recycle):
    specs = vehicle_specs()
    positions = [s['start'] for s in specs]
    odometers = [0.0]*len(specs)
    records = [(tuple(positions), tuple(odometers))]
    for frame in range(2, LAST_FRAME+1):
        for direction in (1, -1):
            indices = sorted((i for i,s in enumerate(specs) if s['direction'] == direction),
                             key=lambda i: positions[i], reverse=True)
            leader = None
            for i in indices:
                spec = specs[i]
                half = VEHICLE_TYPES[spec['kind']][0]/2
                old = positions[i]
                movement = speed/FPS
                if spec['mode'] == 'queue' and frame <= 336:
                    t0, t1 = (frame-2)/335, (frame-1)/335
                    movement = 150*((2*t1-t1*t1)-(2*t0-t0*t0))
                elif spec['mode'] == 'queue' and frame < 1105+spec['index']*20:
                    movement = 0
                wanted = old+movement
                if signal_state(frame) == 'red' and old+half <= -stop_line:
                    wanted = min(wanted, -stop_line-1.5-half)
                if leader is not None:
                    wanted = min(wanted, positions[leader]-VEHICLE_TYPES[specs[leader]['kind']][0]/2-gap-half)
                wanted = max(old, wanted)
                if recycle:
                    wanted = min(wanted, 211.0)
                odometers[i] += wanted-old
                positions[i] = wanted
                leader = i
            # Teleports occur only with the complete body inside the two opaque
            # road-end portals. Defer re-entry until the tail has enough space.
            if recycle:
                for i in indices:
                    if positions[i] < 211:
                        continue
                    half = VEHICLE_TYPES[specs[i]['kind']][0]/2
                    others = [j for j in indices if j != i]
                    if all(positions[j]-VEHICLE_TYPES[specs[j]['kind']][0]/2 >= -211+half+gap for j in others):
                        positions[i] = -211.0
        records.append((tuple(positions), tuple(odometers)))
    return tuple(records)


def vehicle_sample(spec, frame):
    settings = _settings()
    records = _schedule(float(settings.get('speed',18)), float(settings.get('minimum_gap',4)),
                        float(settings.get('stop_line',55)), bool(settings.get('recycle',True)))
    index = next(i for i,s in enumerate(vehicle_specs()) if s['name'] == spec['name'])
    f = max(1.0, min(float(frame), LAST_FRAME))
    lo, hi = int(f)-1, min(int(f), LAST_FRAME-1)
    alpha = f-int(f)
    p0,d0 = records[lo][0][index], records[lo][1][index]
    p1,d1 = records[hi][0][index], records[hi][1][index]
    # Fractional frames never interpolate a wrap across the visible road.
    position = p0 if p1 < p0 else p0+(p1-p0)*alpha
    return position, d0+(d1-d0)*alpha


def longitudinal_position(spec, frame):
    return vehicle_sample(spec, frame)[0]


def vehicle_position(spec, frame):
    direction = spec['direction']
    return (direction*longitudinal_position(spec, frame), direction*2.8, ROAD_Z)


def braking(spec, frame):
    return signal_state(frame) == 'red' and longitudinal_position(spec,frame) < -_settings().get('stop_line',55)


def _linear(ob):
    # Blender 4/5 actions expose fcurves differently; inserted frame samples are
    # sufficient either way. Explicit linear interpolation prevents overshoot.
    action = ob.animation_data.action if ob.animation_data else None
    if not action:
        return
    curves = list(getattr(action, 'fcurves', ()))
    for layer in getattr(action, 'layers', ()):
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', ()):
                curves.extend(bag.fcurves)
    for curve in curves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'


def build(g):
    import bpy
    from .scenario import END, reference_frame, CONFIG, dusk
    def actual_frame(reference):
        return max(1, round(reference*END/1440))
    group, box, cyl, empty = (g[k] for k in ('group', 'box', 'cyl', 'empty'))
    material = g['material']
    dark, glass, rubber, white = (g[k] for k in ('dark', 'glass', 'rubber', 'white'))
    bodymats = {
        'bus': g['red'],
        'taxi': material('Traffic | black London taxi', (.018, .025, .033), .35, .26),
        'car': material('Traffic | teal compact', (.03, .31, .30), .42, .25),
        'truck': material('Traffic | cream delivery truck', (.72, .66, .47), .2, .42),
    }
    chrome = material('Traffic | wheel hubs', (.37, .41, .43), .8, .24)

    def lamp(name, color, strength):
        mat = material(name, color, .1, .3)
        bs = mat.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Emission Color'].default_value = (*color, 1)
        bs.inputs['Emission Strength'].default_value = strength
        return mat

    headlights = lamp('Traffic | evening headlights', (1, .87, .61), .15)
    headinput = headlights.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength']
    for f in sorted(set([1, END]+list(range(1,END+1,6)))):
        headinput.default_value = .15+4.85*dusk(f)
        headinput.keyframe_insert('default_value', frame=f)

    actors = []
    for spec in vehicle_specs():
        kind, direction = spec['kind'], spec['direction']
        length, width, height = VEHICLE_TYPES[kind]
        root = empty(spec['name'], 'Traffic', vehicle_position(spec, 1))
        root.rotation_euler.z = 0 if direction == 1 else math.pi
        root['actor_type'] = 'vehicle'
        root['vehicle_type'] = kind
        root['type'] = kind
        root['length'], root['width'], root['direction'] = length, width, direction
        root['height'] = height
        root['schedule_mode'] = spec['mode']
        root['stop_line'] = -direction*_settings().get('stop_line',55)
        group(spec['name']+' body', 'Traffic', root)
        mat = bodymats[kind]
        radius = .50 if kind in ('bus', 'truck') else .35
        box((0, 0, .65), (length, width, .65), mat)
        if kind == 'bus':
            box((-.2, 0, 2.45), (length-.6, width, 3.5), mat)
            for z in (1.9, 3.35):
                for x in (-4.0, -2.5, -1, .5, 2, 3.5):
                    for side in (-1, 1):
                        box((x, side*(width/2+.012), z), (1.16, .035, .9), glass)
                box((length/2-.28, 0, z), (.04, width-.25, .85), glass)
            box((length/2-.24, 0, 2.65), (.05, 1.65, .32), dark)
        elif kind == 'truck':
            box((-1, 0, 1.95), (length-2.1, width, 2.4), mat)
            box((length/2-1.0, 0, 1.42), (1.9, width-.1, 1.9), mat)
            box((length/2-.035, 0, 1.95), (.05, width-.35, .85), glass)
            for side in (-1, 1):
                box((length/2-1.0, side*width/2, 1.98), (1.15, .035, .75), glass)
        else:
            box((-.25, 0, 1.12), (length*.58, width*.89, height-.75), mat)
            box((length*.24, 0, 1.23), (.06, width*.78, .5), glass)
            for side in (-1, 1):
                box((-.32, side*width*.45, 1.28), (length*.45, .035, .45), glass)
            if kind == 'taxi':
                box((-.2, 0, height+.05), (.6, .4, .16), g['gold'])
        # Lamps are at the forward and rear ends of each local vehicle.
        stopmat = lamp(spec['name']+' | brake lamps', (1, .012, .008), .3)
        stopinput = stopmat.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength']
        release = 1105+spec.get('index', 0)*20
        for frame in range(1, END+1):
            stopinput.default_value = 4 if braking(spec, reference_frame(frame)) else .3
            stopinput.keyframe_insert('default_value', frame=frame)
        for side in (-1, 1):
            box((length/2+.018, side*width*.33, .82), (.04, .35, .22), headlights)
            box((-length/2-.018, side*width*.33, .82), (.04, .30, .2), stopmat)
        for side in (-1, 1):
            data = bpy.data.lights.new(spec['name']+f' headlight {side}', 'SPOT')
            data.color = (1.0, .87, .61)
            data.spot_size = math.radians(48)
            data.spot_blend = .55
            data.shadow_soft_size = .12
            light = bpy.data.objects.new(data.name, data)
            bpy.context.collection.objects.link(light)
            light.parent = root
            light['lighting_role'] = 'headlight'
            light.location = (length/2+.08, side*width*.33, .85)
            from mathutils import Vector
            light.rotation_euler = Vector((1, 0, -.08)).to_track_quat('-Z','Y').to_euler()
            data.use_shadow = False
            for f in sorted(set([1, END]+list(range(1,END+1,6)))):
                data.energy = CONFIG['traffic']['headlight_power']*CONFIG['lighting']['night_strength']*dusk(f)
                data.keyframe_insert('energy', frame=f)
        wheels = []
        for x in (-length*.32, length*.32):
            for side in (-1, 1):
                wheel = empty(spec['name']+f' wheel {x:.2f} {side}', 'Traffic')
                wheel.parent = root
                wheel['wheel_radius'] = radius
                wheel['actor_type'] = 'wheel'
                wheel.location = (x, side*width*.49, radius)
                group(wheel.name, 'Traffic', wheel)
                cyl((0, 0, 0), radius, .23, rubber, 20, axis=(0, 1, 0))
                cyl((0, side*.13, 0), radius*.55, .035, chrome, 12, axis=(0, 1, 0))
                # A visible radial spoke makes the wheel's rotation readable.
                box((0, side*.16, radius*.25), (.075, .025, radius*.75), dark)
                wheels.append(wheel)
        start = longitudinal_position(spec, reference_frame(1))
        for frame in range(1, END+1):
            ref = reference_frame(frame)
            root.location = vehicle_position(spec, ref)
            root.keyframe_insert('location', frame=frame)
            # Fade-free spawning happens entirely inside the covered portal:
            # both bumpers must stay behind its entrance and before its rear wall.
            visible = abs(root.location.x) < 211-1e-6
            root.scale = (1, 1, 1) if visible else (0, 0, 0)
            root.keyframe_insert('scale', frame=frame)
            root['odometer'] = vehicle_sample(spec, ref)[1]
            root.keyframe_insert(data_path='["odometer"]', frame=frame)
            angle = vehicle_sample(spec, ref)[1]/radius
            for wheel in wheels:
                wheel.rotation_euler.y = angle
                wheel.keyframe_insert('rotation_euler', frame=frame, index=1)
        _linear(root)
        for wheel in wheels:
            _linear(wheel)
        actors.append(root)

    # Each half-road barrier spans just its incoming lane; its pivot lies
    # outside the lane and on the approach side of the stone tower.
    for direction in (1, -1):
        x, side = -direction*51.0, direction
        group(f'Barrier {direction:+d} pedestal', 'Traffic infrastructure')
        box((x, side*5.8, ROAD_Z+.55), (.75, .65, 1.1), g['blue'])
        hinge = empty(f'Barrier {direction:+d} pivot', 'Traffic infrastructure',
                      (x, side*5.8, ROAD_Z+1.1))
        hinge['actor_type'] = 'barrier'
        group(f'Barrier {direction:+d} arm', 'Traffic infrastructure', hinge)
        box((0, -side*2.7, 0), (.19, 5.4, .20), white)
        for j in range(9):
            box((-.005, -side*(.3+j*.6), 0), (.205, .28, .22), g['red'])
        hinge['direction'] = direction
        for frame in range(1, END+1):
            hinge.rotation_euler.x = -side*barrier_angle(reference_frame(frame))
            hinge.keyframe_insert('rotation_euler', frame=frame, index=0)
        _linear(hinge)
        group(f'Stop line {direction:+d}', 'Traffic infrastructure')
        box((-direction*_settings().get('stop_line',55), side*2.8, ROAD_Z+.035), (.32, 5.15, .035), white)
        sx, sy = -direction*57, side*6.25
        cyl((sx, sy, ROAD_Z+1.8), .09, 3.6, g['dark'])
        box((sx, sy, ROAD_Z+3.65), (.35, .65, 1.55), dark)
        for state, z, color in (('red', 4.1, (1, .015, .005)),
                                 ('amber', 3.65, (1, .46, .005)),
                                 ('green', 3.2, (.02, 1, .15))):
            mat = lamp(f'Signal {direction:+d} {state}', color, .03)
            # Lens faces the approaching traffic along the X axis.
            cyl((sx-direction*.2, sy, ROAD_Z+z), .20, .06, mat, 20, axis=(1, 0, 0))
            socket = mat.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength']
            for frame in range(1, END+1):
                ref = reference_frame(frame)
                enabled = state == signal_state(ref) or (state == 'amber' and 193 <= ref <= 216)
                socket.default_value = 5 if enabled else .015
                socket.keyframe_insert('default_value', frame=frame)
            # Constant interpolation gives an unambiguous frame boundary.
            action = mat.node_tree.animation_data.action
            for layer in getattr(action, 'layers', ()):
                for strip in layer.strips:
                    for bag in getattr(strip, 'channelbags', ()):
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation = 'CONSTANT'
    return actors
