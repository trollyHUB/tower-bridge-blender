"""Distance-driven pedestrian paths and planted-foot targets, without Blender."""
import math


def route_state(keys, frame):
    """Return eased position and travelled distance; each stop has zero speed."""
    distance = 0.0
    for (a, p), (b, q) in zip(keys, keys[1:]):
        length = math.dist(p, q)
        if frame <= b:
            t = max(0.0, min(1.0, (frame-a)/(b-a)))
            t = t*t*(3-2*t)
            return tuple(x+(y-x)*t for x,y in zip(p,q)), distance+length*t
        distance += length
    return tuple(keys[-1][1]), distance


def foot_target(distance, side, cycle=.95, stance=.60):
    """Forward world-distance and lift; stance target stays exactly fixed."""
    shifted = distance + (cycle*.5 if side > 0 else 0)
    n = math.floor(shifted/cycle)
    phase = shifted/cycle-n
    anchor = n*cycle + cycle*stance*.5 - (cycle*.5 if side > 0 else 0)
    if phase <= stance:
        return anchor, 0.0
    t = (phase-stance)/(1-stance)
    eased = t*t*(3-2*t)
    return anchor+cycle*eased, .13*math.sin(math.pi*t)


def leg_angles(forward, lift, hip=.76, length=.43):
    """Two equal segments meet the exact foot target in the sagittal plane."""
    down = hip-lift
    distance = min(2*length-.00001, math.hypot(forward, down))
    bend = math.acos(distance/(2*length))
    return math.atan2(forward, down)-bend, 2*bend
