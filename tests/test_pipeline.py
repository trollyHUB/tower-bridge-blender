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


if __name__ == '__main__':
    unittest.main()

