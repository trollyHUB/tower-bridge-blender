"""Build an independent, editable weather/population variant of the scene."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scene_components.settings import load_config
from scene_components.presets import WEATHER, DENSITY, apply_presets


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--weather', choices=WEATHER, default='overcast')
    p.add_argument('--density', choices=DENSITY, default='sparse')
    p.add_argument('--lighting', choices=['day', 'evening', 'animated'], default='day')
    p.add_argument('--blender', default=r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
    p.add_argument('--output', type=Path)
    p.add_argument('--render', action='store_true')
    args = p.parse_args()
    out = (args.output or ROOT/'Tower_Bridge/extensions/weather'/f'{args.weather}_{args.density}').resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg = apply_presets(load_config(ROOT/'config/scene.json'), args.weather, args.density, args.lighting)
    path = out/'scene.json'
    path.write_text(json.dumps(cfg, indent=2)+'\n', encoding='utf-8')
    env = dict(os.environ, TOWER_BRIDGE_CONFIG=str(path), TOWER_BRIDGE_OUTPUT=str(out))
    subprocess.run([args.blender, '--background', '--threads', '2', '--python-exit-code', '1', '--python', str(ROOT/'build_tower_bridge.py')], env=env, check=True)
    command = [args.blender, '--background', '--threads', '2', '--python-exit-code', '1', '--python', str(ROOT/'tools/check_preset.py')]
    if args.render:
        command += ['--', '--render']
    subprocess.run(command, env=env, check=True)


if __name__ == '__main__':
    main()
