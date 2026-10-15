"""Dry weather and city population presets; no Blender dependency."""
from copy import deepcopy

WEATHER = {
    'clear': {'sky': (.49, .65, .82, 1), 'world': 1., 'sun': 1., 'fill': 1., 'sun_angle': .00918},
    'overcast': {'sky': (.54, .60, .66, 1), 'world': 1.65, 'sun': .18, 'fill': .72, 'sun_angle': .35},
}
DENSITY = {
    'sparse': {'vehicles_per_direction': 3, 'bank_walkers': 2, 'passengers_per_stop': 1, 'cafe_visitors': 1},
    'standard': {'vehicles_per_direction': 5, 'bank_walkers': 6, 'passengers_per_stop': 2, 'cafe_visitors': 3},
    'busy': {'vehicles_per_direction': 7, 'bank_walkers': 8, 'passengers_per_stop': 3, 'cafe_visitors': 4},
}


def apply_presets(config, weather='clear', density='busy', lighting=None):
    if weather not in WEATHER or density not in DENSITY:
        raise ValueError('Unknown weather or density preset')
    cfg = deepcopy(config)
    cfg['weather'] = {'preset': weather}
    cfg['population'] = {'preset': density}
    values = DENSITY[density]
    cfg['traffic']['vehicles_per_direction'] = values['vehicles_per_direction']
    for key in ('bank_walkers', 'passengers_per_stop', 'cafe_visitors'):
        cfg['people'][key] = values[key]
    if lighting is not None:
        if lighting not in ('day', 'evening', 'animated'):
            raise ValueError('Unknown lighting preset')
        cfg['lighting']['mode'] = lighting
    return cfg


def build(g):
    """Apply sky/light changes after practical lighting has inserted its keys."""
    from .scenario import CONFIG
    import json
    cfg = WEATHER[CONFIG.get('weather', {}).get('preset', 'clear')]
    scene = g['scene']
    bg = scene.world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = cfg['sky']
    # Multiply existing keys, retaining the animated day/evening transition.
    def scale_keys(id_data, path, factor):
        action = id_data.animation_data.action if id_data.animation_data else None
        if not action:
            return
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, 'channelbags', ()):
                    for curve in bag.fcurves:
                        if curve.data_path == path:
                            for key in curve.keyframe_points:
                                key.co.y *= factor
                                key.handle_left.y *= factor
                                key.handle_right.y *= factor
    scale_keys(scene.world.node_tree, 'nodes["Background"].inputs[1].default_value', cfg['world'])
    bg.inputs['Strength'].default_value *= cfg['world']
    for light in g['bpy'].data.lights:
        if light.type == 'SUN':
            light.angle = cfg['sun_angle']
            scale_keys(light, 'energy', cfg['sun'])
            light.energy *= cfg['sun']
        elif light.type == 'AREA' and light.name in ('Key | warm softbox', 'Rim | tower silhouette'):
            scale_keys(light, 'energy', cfg['fill'])
            light.energy *= cfg['fill']
    scene['Weather preset'] = CONFIG.get('weather', {}).get('preset', 'clear')
    scene['Population preset'] = CONFIG.get('population', {}).get('preset', 'busy')
    scene['Weather contract'] = json.dumps(cfg)
