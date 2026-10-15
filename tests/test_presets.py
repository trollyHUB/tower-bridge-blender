"""Preset variation must change populations and preserve the master config."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from scene_components.presets import WEATHER, DENSITY, apply_presets
from scene_components.settings import load_config


class PresetTests(unittest.TestCase):
    def test_all_six_combinations_are_valid_and_leave_master_untouched(self):
        master = load_config()
        original = copy.deepcopy(master)
        for weather in WEATHER:
            for density in DENSITY:
                cfg = apply_presets(master, weather, density, 'day')
                with patch.object(Path, 'read_text', return_value=json.dumps(cfg)):
                    self.assertEqual(load_config('variant.json'), cfg)
                self.assertEqual(cfg['traffic']['vehicles_per_direction'], DENSITY[density]['vehicles_per_direction'])
        self.assertEqual(master, original)

    def test_sparse_reduces_both_people_and_traffic(self):
        master = load_config()
        sparse, busy = (apply_presets(master, density=d) for d in ('sparse', 'busy'))
        self.assertLess(sparse['traffic']['vehicles_per_direction'], busy['traffic']['vehicles_per_direction'])
        for key in ('bank_walkers', 'passengers_per_stop', 'cafe_visitors'):
            self.assertLess(sparse['people'][key], busy['people'][key])

    def test_bad_weather_density_and_count_are_rejected(self):
        for kwargs in ({'weather': 'snow'}, {'density': 'empty'}, {'lighting': 'noon'}):
            with self.assertRaises(ValueError):
                apply_presets(load_config(), **kwargs)
        cfg = load_config()
        for value in (True, 0, 8, 3.5):
            cfg['traffic']['vehicles_per_direction'] = value
            with patch.object(Path, 'read_text', return_value=json.dumps(cfg)), self.assertRaises(ValueError):
                load_config('invalid.json')
