"""Exporter axis/winding and checked export contracts, without a Blender dependency."""
import importlib.util
import json
import pathlib
import unittest
import hashlib
import math
import struct

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('export_unity', ROOT/'tools/export_unity.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class UnityExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = ROOT/'Unity/Assets/StreamingAssets'
        cls.data = json.loads((cls.folder/'scene.json').read_text()) if (cls.folder/'scene.json').exists() else None

    def test_metre_axis_mapping(self):
        self.assertEqual(module.unity_point((1, 2, 3)), (1, 3, 2))

    def test_export_binary_and_samples(self):
        folder = ROOT/'Unity/Assets/StreamingAssets'
        if not (folder/'scene.json').exists():
            self.skipTest('Run Blender export first')
        data = json.loads((folder/'scene.json').read_text())
        self.assertEqual(data['units'], 'metres')
        self.assertEqual(sum('bascule hinge' in g['name'] for g in data['groups']), 2)
        size = (folder/'scene.bin').stat().st_size
        for group in data['groups']:
            for part in group['parts']:
                self.assertEqual(part['count'] % 3, 0)
                self.assertLessEqual(part['offset'] + part['count']*12, size)
            if group['actor_type'] != 'static':
                self.assertEqual(len(group['samples']), data['end_frame'])

    def test_export_is_current_source(self):
        self.assertIsNotNone(self.data)
        source = ROOT/'Tower_Bridge/Tower_Bridge.blend'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), self.data['source_sha256'])

    def test_hinges_preserve_scale_pivots_and_motion(self):
        hinges = [g for g in self.data['groups'] if 'bascule hinge' in g['name']]
        self.assertEqual(len(hinges), 2)
        self.assertEqual(sorted(round(g['samples'][0]['p'][0], 1) for g in hinges), [-30.5, 30.5])
        for group in hinges:
            initial, raised = group['samples'][0], group['samples'][719]
            self.assertAlmostEqual(initial['p'][1], 10)
            self.assertEqual(initial['s'], [1, 1, 1])
            dot = abs(sum(a*b for a, b in zip(initial['q'], raised['q'])))
            degrees = math.degrees(2*math.acos(min(1, dot)))
            self.assertAlmostEqual(degrees, 68, places=3)
            self.assertEqual(initial['p'], raised['p'])

    def test_binary_coordinates_finite_and_metres(self):
        mesh = (self.folder/'scene.bin').read_bytes()
        values = struct.unpack('<'+'f'*(len(mesh)//4), mesh)
        self.assertTrue(all(math.isfinite(v) for v in values))
        self.assertGreater(max(values), 100)
        # Source includes a 4 km backdrop plane, whose half extent is 2000 m.
        self.assertLessEqual(max(abs(v) for v in values), 2000)

    def test_articulated_actors_and_materials_present(self):
        actors = {g['actor_type'] for g in self.data['groups']}
        self.assertTrue({'vehicle','wheel','bus_door','sailboat','launch','barrier','hinge'} <= actors)
        for mat in self.data['materials']:
            self.assertTrue(mat['name'])
            self.assertEqual(len(mat['color']), 4)
            self.assertTrue(all(math.isfinite(v) for v in mat['color']))

    def test_baked_vehicle_visibility_and_portals(self):
        vehicles = [g for g in self.data['groups'] if g['actor_type'] == 'vehicle']
        self.assertGreaterEqual(len(vehicles), 10)
        self.assertTrue(any(any(p['s'][0] == 0 for p in g['samples']) for g in vehicles))
        # Samples contain portal discontinuities; the runtime explicitly keeps
        # the previous pose until the boundary instead of crossing the scene.
        self.assertTrue(any(any(abs(a['p'][0]-b['p'][0])>100 for a,b in zip(g['samples'],g['samples'][1:])) for g in vehicles))


if __name__ == '__main__':
    unittest.main()
