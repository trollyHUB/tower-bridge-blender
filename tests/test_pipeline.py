"""Regression checks for stale, incomplete and corrupt render deliverables."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from scene_components.render_manifest import make_identity, cache_directory, png_size, check_frames


def png(width=2, height=2):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\x00' + b'\x80' * width * 3) * height)) + chunk(b'IEND', b''))


class RenderManifestTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / 'research'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scene = self.root / 'scene.blend'
        self.config = self.root / 'scene.json'
        self.script = self.root / 'render.py'
        self.scene.write_bytes(b'scene version one')
        self.script.write_text('renderer version one')
        self.config.write_text(json.dumps({'fps': 24, 'duration_seconds': 60,
            'render': {'width': 1920, 'height': 1080, 'preview_scale': 25}}))

    def identity(self, profile='final'):
        return make_identity(self.scene, self.config, self.script, profile, '5.2')

    def test_scene_config_renderer_and_profile_invalidate_cache(self):
        previous = cache_directory(self.root / 'cache', self.identity())
        self.assertEqual(previous, cache_directory(self.root / 'cache', self.identity()))
        for path in (self.scene, self.script):
            path.write_bytes(path.read_bytes() + b'changed')
            current = cache_directory(self.root / 'cache', self.identity())
            self.assertNotEqual(current, previous)
            previous = current
        cfg = json.loads(self.config.read_text())
        cfg['render']['preview_scale'] = 50
        self.config.write_text(json.dumps(cfg))
        current = cache_directory(self.root / 'cache', self.identity())
        self.assertNotEqual(current, previous)
        self.assertNotEqual(current, cache_directory(self.root / 'cache', self.identity('preview')))
        self.assertEqual(self.identity('preview')['size'], [960, 540])
        self.assertEqual(self.identity()['frames'], 1440)

    def test_tampered_manifest_rejected(self):
        directory = cache_directory(self.root, self.identity())
        (directory / 'manifest.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Incompatible'):
            cache_directory(self.root, self.identity())

    def test_complete_sequence_and_missing_or_wrong_size_frames(self):
        (self.root / '0001.png').write_bytes(png())
        with self.assertRaisesRegex(ValueError, 'Missing frame'):
            check_frames(self.root, 2, [2, 2])
        (self.root / '0002.png').write_bytes(png(3, 2))
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            check_frames(self.root, 2, [2, 2])
        (self.root / '0002.png').write_bytes(png())
        check_frames(self.root, 2, [2, 2])

    def test_truncated_and_corrupt_png_rejected(self):
        path = self.root / 'bad.png'
        original = png()
        for data in (original[:24], original[:-4], original[:40] + b'\xff' + original[41:]):
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                png_size(path)

    def test_valid_crc_but_incomplete_pixel_stream_rejected(self):
        data = png()
        start = data.index(b'IDAT')
        length = struct.unpack('>I', data[start - 4:start])[0]
        compressed = data[start + 4:start + 4 + length][:-2]
        replacement = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', zlib.crc32(b'IDAT' + compressed) & 0xffffffff)
        path = self.root / 'incomplete.png'
        path.write_bytes(data[:start - 4] + replacement + data[start + 8 + length:])
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            png_size(path)


class SupportedConfigTests(unittest.TestCase):
    def test_manifest_uses_rounded_shared_frame_count(self):
        # Binary floating-point yields 28.999999999999996, not 29.
        cfg = {'fps': 50, 'duration_seconds': .58,
               'render': {'width': 1280, 'height': 720, 'preview_scale': 50}}
        from scene_components.settings import frame_count
        import tempfile
        scratch = Path(__file__).resolve().parents[1] / 'research'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            directory=Path(temp)
            scene=directory/'scene.blend';scene.write_bytes(b'scene')
            config=directory/'scene.json';config.write_text(json.dumps(cfg))
            result=make_identity(scene,config,scene,'preview','5.2')
        self.assertEqual(frame_count(cfg),29)
        self.assertEqual(result['frames'],29)
        self.assertEqual(result['size'],[640,360])

    def test_reject_unsupported_engine_and_actual_odd_preview_dimensions(self):
        from scene_components.settings import load_config
        import copy
        root=Path(__file__).resolve().parents[1]
        baseline=load_config()
        scratch=root/'research';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            path=Path(temp)/'scene.json'
            for settings in ({'engine':'WORKBENCH'}, {'preview_scale':25.5},
                             {'width':1924,'preview_scale':25},
                             {'width':16,'height':16,'preview_scale':1}):
                cfg=copy.deepcopy(baseline);cfg['render'].update(settings)
                path.write_text(json.dumps(cfg))
                with self.subTest(settings=settings), self.assertRaises(ValueError):
                    load_config(path)
            cfg=copy.deepcopy(baseline)
            cfg.update(fps=30,duration_seconds=45)
            cfg['render'].update(width=1280,height=720,preview_scale=50,engine='CYCLES')
            path.write_text(json.dumps(cfg))
            self.assertEqual(load_config(path)['fps'],30)


class RenderSettingsTests(unittest.TestCase):
    """Execute real engine-policy functions with Blender settings represented by RNA-like objects."""
    def setUp(self):
        import ast
        from types import SimpleNamespace as NS
        self.NS = NS
        source = Path(__file__).resolve().parents[1] / 'render_tower_bridge.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in ('cycles_device', 'engine')]
        self.config = {'render': {'samples': 16, 'preview_samples': 3, 'still_samples': 27,
                                 'device': 'auto', 'engine': 'EEVEE', 'preview_scale': 50}}
        self.scope = {'cfg': self.config, 'profile': 'final', 'WIDTH': 1280, 'HEIGHT': 720, 'FPS': 30,
                      'bpy': NS(context=NS(preferences=NS(addons={}))) }
        exec(compile(ast.Module(body=funcs, type_ignores=[]), str(source), 'exec'), self.scope)
        self.scene = NS(render=NS(image_settings=NS()), cycles=NS(),
                        eevee=NS(taa_samples=7, taa_render_samples=8))

    def test_preview_samples_resolution_and_integer_timebase(self):
        self.scope['profile'] = 'preview'
        self.scope['engine'](self.scene)
        self.assertEqual(self.scene.eevee.taa_render_samples, 3)
        self.assertEqual(self.scene.render.resolution_percentage, 50)
        self.assertEqual(self.scene.render.fps, 30)
        self.assertEqual(self.scene.render.fps_base, 1)
        self.assertEqual(self.scene.render.resolution_x, 1280)

    def test_still_samples_respected_below_previous_minimum(self):
        self.config['render']['still_samples'] = 2
        self.scope['engine'](self.scene, still=True)
        self.assertEqual(self.scene.render.engine, 'CYCLES')
        self.assertEqual(self.scene.cycles.samples, 2)
        self.assertEqual(self.scene.cycles.device, 'CPU')

    def test_cpu_request_does_not_probe_gpu_and_uses_configured_samples(self):
        self.config['render']['device'] = 'cpu'
        self.scope['engine'](self.scene)
        self.assertEqual(self.scene.render.engine, 'CYCLES')
        self.assertEqual(self.scene.cycles.device, 'CPU')
        self.assertEqual(self.scene.cycles.samples, 16)

    def test_explicit_gpu_does_not_silently_fall_back(self):
        self.config['render'].update(device='gpu', engine='CYCLES')
        with self.assertRaisesRegex(RuntimeError, 'requires an available'):
            self.scope['engine'](self.scene)

    def test_cycle_preview_applies_preview_quality(self):
        self.config['render']['engine'] = 'CYCLES'
        self.scope['profile'] = 'preview'
        self.scope['engine'](self.scene)
        self.assertEqual(self.scene.cycles.samples, 3)


if __name__ == '__main__':
    unittest.main()
