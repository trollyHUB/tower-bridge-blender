"""Pure render-cache identity and complete PNG checks, usable without Blender."""
import hashlib
import json
import struct
import zlib
from pathlib import Path


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def make_identity(scene, config_path, implementation, profile, blender_version):
    cfg = json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    scale = int(cfg['render'].get('preview_scale', 25)) if profile == 'preview' else 100
    return {'scene_sha256': sha(scene), 'config_sha256': sha(config_path),
            'implementation_sha256': sha(implementation), 'profile': profile,
            'fps': int(cfg['fps']), 'frames': int(cfg['fps'] * cfg['duration_seconds']),
            'size': [int(cfg['render']['width']) * scale // 100,
                     int(cfg['render']['height']) * scale // 100],
            'blender_version': blender_version}


def cache_directory(root, identity):
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    directory = Path(root) / key
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / 'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text(encoding='utf-8')) != identity:
            raise ValueError('Incompatible frame cache manifest')
    else:
        manifest.write_text(json.dumps(identity, indent=2), encoding='utf-8')
    return directory


def png_size(path):
    """Reject truncated chunks, bad CRCs, absent pixels and incomplete zlib streams."""
    with Path(path).open('rb') as stream:
        if stream.read(8) != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f'Invalid PNG signature: {path}')
        dimensions = None
        pixels = bytearray()
        while True:
            header = stream.read(8)
            if len(header) != 8:
                raise ValueError(f'Truncated PNG: {path}')
            length, kind = struct.unpack('>I4s', header)
            data = stream.read(length)
            checksum = stream.read(4)
            if len(data) != length or len(checksum) != 4:
                raise ValueError(f'Truncated PNG chunk: {path}')
            if zlib.crc32(kind + data) & 0xffffffff != struct.unpack('>I', checksum)[0]:
                raise ValueError(f'PNG CRC mismatch: {path}')
            if kind == b'IHDR':
                width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', data)
                if not width or not height or compression or filtering or interlace:
                    raise ValueError('Unsupported PNG image format')
                dimensions = [width, height]
                channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
                expected_bytes = height * (1 + (width * channels * depth + 7) // 8)
            elif kind == b'IDAT':
                pixels.extend(data)
            elif kind == b'IEND':
                if length or stream.read(1):
                    raise ValueError('Invalid PNG end marker')
                break
    if dimensions is None or not pixels:
        raise ValueError(f'PNG lacks image data: {path}')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(pixels)
    if not decoder.eof or decoder.unused_data or len(raw) != expected_bytes:
        raise ValueError(f'Incomplete PNG pixel stream: {path}')
    return dimensions


def check_frames(directory, count, size):
    for frame in range(1, count + 1):
        path = Path(directory) / f'{frame:04d}.png'
        if not path.is_file():
            raise ValueError(f'Missing frame: {path}')
        if png_size(path) != list(size):
            raise ValueError(f'Wrong frame dimensions: {path}')
