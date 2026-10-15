"""Pure functions: scene timing uses seconds on a 60-second reference timeline."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config/scene.json').read_text(encoding='utf-8'))
FPS = CONFIG['fps']
END = round(FPS * CONFIG['duration_seconds'])

def frame(seconds):
    return max(1, round(seconds / 60 * END))

def smooth(a, b, value):
    t = max(0.0, min(1.0, (value-a)/(b-a)))
    return t*t*(3-2*t)

def reference_frame(f):
    return f * 1440 / END

def opening(f):
    t = reference_frame(f)
    return CONFIG['opening_degrees'] * (smooth(432,624,t)-smooth(864,1056,t))

def dusk(f):
    return smooth(1200,1440,reference_frame(f))

def boat_y(f):
    t = reference_frame(f)
    if t < 624: return -64 + 25*smooth(1,580,t)
    if t <= 864: return -39 + 78*smooth(624,864,t)
    return 39 + 35*smooth(864,1440,t)

PHASES = [(0,'DAY | traffic'),(8,'WARNING | clear deck'),(14,'GATES | close'),
          (18,'LIFT'),(26,'VESSEL PASSAGE'),(36,'LOWER'),(44,'GATES | open'),
          (46,'TRAFFIC RESUMES'),(50,'DUSK'),(60,'FINALE')]

def linear_keys():
    import bpy
    for action in bpy.data.actions:
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag=strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation='LINEAR'
