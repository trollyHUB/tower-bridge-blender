"""Pure functions: scene timing uses seconds on a 60-second reference timeline."""
import json
from pathlib import Path
from .settings import load_config, frame_count

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config()
FPS = CONFIG['fps']
END = frame_count(CONFIG)

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
    mode=CONFIG['lighting']['mode']
    if mode=='day':return 0.
    if mode=='evening':return 1.
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
    # A portal recycle is an instantaneous relocation behind the entrance wall.
    # Do not interpolate the long jump across the entire road at subframes.
    for ob in bpy.data.objects:
        if ob.get('actor_type')!='vehicle' or not ob.animation_data:continue
        action=ob.animation_data.action
        for layer in action.layers:
            for strip in layer.strips:
                bag=strip.channelbag(ob.animation_data.action_slot)
                if not bag:continue
                for curve in bag.fcurves:
                    if curve.data_path!='location' or curve.array_index!=0:continue
                    keys=curve.keyframe_points
                    for first,second in zip(keys,list(keys)[1:]):
                        if abs(second.co.y-first.co.y)>300:first.interpolation='CONSTANT'
