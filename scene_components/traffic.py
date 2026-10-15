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
        front = -STOP_LINE-1.5
        for i, kind in enumerate(('truck', 'taxi', 'car', 'bus')):
            length = VEHICLE_TYPES[kind][0]
            target = front-length/2
            specs.append(dict(name=f'Traffic queue {direction:+d} {i+1} {kind}',
                              kind=kind, direction=direction, mode='queue',
                              start=target-150.0, target=target, index=i))
            front -= length+4.0
    return specs


def longitudinal_position(spec, frame):
    """Distance coordinate increasing in the actor's travel direction."""
    if spec['mode'] == 'through':
        return spec['start']+18.0*(frame-1)/FPS
    # Constant initial speed followed by a gentle deceleration to rest. The
    # trajectory's velocity reaches exactly zero at frame 336.
    t = max(0.0, min(1.0, (frame-1)/335.0))
    approach = 150.0*(2*t-t*t)
    release = 1105+spec['index']*20
    seconds = max(0.0, (frame-release)/FPS)
    acceleration = 2.5
    cruise = 18.0
    ramp = cruise/acceleration
    departure = (.5*acceleration*seconds**2 if seconds < ramp
                 else .5*acceleration*ramp*ramp+cruise*(seconds-ramp))
    return spec['start']+approach+departure


def vehicle_position(spec, frame):
    direction = spec['direction']
    return (direction*longitudinal_position(spec, frame), direction*2.8, ROAD_Z)


def braking(spec, frame):
    return spec['mode'] == 'queue' and 193 <= frame < 1105+spec['index']*20


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
    from .scenario import END, reference_frame
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
    for frame, value in ((1, .15), (1200, .15), (1320, 5), (1440, 5)):
        headinput.default_value = value
        headinput.keyframe_insert('default_value', frame=actual_frame(frame))

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
        root['stop_line'] = -direction*STOP_LINE
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
            # The city approach terminates beyond the camera envelope. Cull
            # only when the complete vehicle has passed that distant edge.
            visible = abs(root.location.x) <= 210+length/2
            root.scale = (1, 1, 1) if visible else (0, 0, 0)
            root.keyframe_insert('scale', frame=frame)
            angle = (longitudinal_position(spec, ref)-start)/radius
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
        box((-direction*STOP_LINE, side*2.8, ROAD_Z+.035), (.32, 5.15, .035), white)
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
