"""Inspect actual baked population and weather endpoints in a variant .blend."""
import json
import math
import os
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scene_components.settings import load_config
from scene_components.presets import WEATHER
from scene_components.render_manifest import sha
from scene_components.scenario import dusk

cfg = load_config()
out = Path(os.environ['TOWER_BRIDGE_OUTPUT'])
path = out/'Tower_Bridge.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
scene = bpy.context.scene
assert json.loads(scene['Configuration']) == cfg
objects = list(scene.objects)
counts = {
    'vehicles': len([o for o in objects if o.get('actor_type') == 'vehicle']),
    'walkers': len([o for o in objects if o.get('role') == 'walker']),
    'waiting': len([o for o in objects if o.get('role') == 'bus_stop_waiting']),
    'cafe': len([o for o in objects if o.get('role') == 'cafe_seated']),
}
assert counts == {'vehicles': 2*cfg['traffic']['vehicles_per_direction'],
                  'walkers': 2+cfg['people']['bank_walkers'],
                  'waiting': 2*cfg['people']['passengers_per_stop'],
                  'cafe': cfg['people']['cafe_visitors']}, counts
weather = WEATHER[cfg['weather']['preset']]
endpoints = []
for f in (1, scene.frame_end):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    sun = next(light for light in bpy.data.lights if light.type == 'SUN')
    expected_sun = (2*cfg['lighting']['day_strength']*(1-dusk(f))+.32*cfg['lighting']['night_strength']*dusk(f))*weather['sun']
    bg = scene.world.node_tree.nodes['Background']
    expected_world = (.35*cfg['lighting']['day_strength']*(1-dusk(f))+.18*cfg['lighting']['night_strength']*dusk(f))*weather['world']
    assert abs(sun.energy-expected_sun) < 1e-5, (sun.energy, expected_sun)
    assert abs(bg.inputs['Strength'].default_value-expected_world) < 1e-5
    assert max(abs(a-b) for a,b in zip(bg.inputs['Color'].default_value, weather['sky'])) < 1e-5
    endpoints.append({'frame': f, 'sun_energy': sun.energy, 'world_strength': bg.inputs['Strength'].default_value})
# The shared geometry validators include this density's buses, following gaps,
# pedestrians and boat/bridge clearances at every supported integer frame.
from scene_components.validation import validate
validate(scene, out)
if '--render' in sys.argv:
    for marker in scene.timeline_markers:
        marker.camera = None
    scene.camera = bpy.data.objects['01 | Hero camera']
    scene.frame_set(1)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    try:
        pref = bpy.context.preferences.addons['cycles'].preferences
        pref.compute_device_type = 'OPTIX'
        pref.get_devices()
        for dev in pref.devices:
            dev.use = dev.type == 'OPTIX'
        if not any(dev.use for dev in pref.devices):
            scene.cycles.device = 'CPU'
    except Exception:
        scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(out/'Weather.png')
    bpy.ops.render.render(write_still=True)
scene.frame_set(1)
scene.camera = bpy.data.objects['01 | Hero camera']
scene.render.engine = 'BLENDER_EEVEE'
scene['Preset instructions'] = 'Editable variant. See docs/PRESETS.md to build other weather/population combinations.'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(path))
# Validation was run before saving helpful view defaults; update its scene identity.
validation = json.loads((out/'validation.json').read_text(encoding='utf-8'))
validation['scene_sha256'] = sha(path)
(out/'validation.json').write_text(json.dumps(validation, indent=2), encoding='utf-8')
report = {'passed': True, 'weather': cfg['weather']['preset'], 'density': cfg['population']['preset'],
          'counts': counts, 'endpoints': endpoints, 'scene_sha256': sha(path),
          'render_sha256': sha(out/'Weather.png') if '--render' in sys.argv else None,
          'scope': 'Actual .blend population, world and sun endpoints plus full integer-frame scene validation; dry weather only.'}
(out/'preset_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PRESET_OK', json.dumps(report), flush=True)
