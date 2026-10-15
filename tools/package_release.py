"""Package only a complete release verified against the current source scene."""
from pathlib import Path
import hashlib
import json
import zipfile
import sys

root = Path(__file__).resolve().parent.parent
out = root / 'Tower_Bridge'
sys.path.insert(0,str(root))
from scene_components.render_manifest import png_size
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

cfg = json.loads((root / 'config' / 'scene.json').read_text(encoding='utf-8-sig'))
video = json.loads((out / 'video_validation.json').read_text(encoding='utf-8'))
count = int(cfg['fps'] * cfg['duration_seconds'])
size = [cfg['render']['width'], cfg['render']['height']]
assert count == 1440 and cfg['fps'] == 24 and size == [1920, 1080], 'Release requires 60 seconds at 24 fps, Full HD'
assert video['frames'] == count and video['size'] == size and abs(video['fps'] - cfg['fps']) < .001
assert video['identity']['scene_sha256'] == sha(out / 'Tower_Bridge.blend'), 'Scene changed after encoding'
assert video['identity']['config_sha256'] == sha(root / 'config' / 'scene.json'), 'Configuration changed after encoding'
assert video['identity']['profile'] == 'final'
assert video['identity']['implementation_sha256'] == sha(root / 'render_tower_bridge.py'), 'Renderer changed after encoding'
assert video['identity']['manifest_implementation_sha256'] == sha(root / 'scene_components' / 'render_manifest.py'), 'Cache implementation changed after encoding'
assert sha(out / 'Tower_Bridge_Animation.mp4') == video['video_sha256'], 'Video hash mismatch'
assert (out / 'Tower_Bridge_Animation.mp4').stat().st_size == video['bytes']
assert len(video.get('decoded_frames', [])) >= 7, 'Run VideoCheck before packaging'
for name in ('Open', 'Closed', 'City', 'Water', 'Evening'):
    assert (out / 'renders' / f'Tower_Bridge_{name}.png').is_file(), f'Missing {name} still'
    assert png_size(out/'renders'/f'Tower_Bridge_{name}.png') == size, f'Invalid {name} still'
assert (out / 'validation.json').is_file(), 'Run validation before packaging'
validation=json.loads((out/'validation.json').read_text(encoding='utf-8'))
assert validation['passed'] and validation['scene_sha256']==sha(out/'Tower_Bridge.blend'), 'Stale scene validation'
files = [root / name for name in ('build_tower_bridge.py', 'render_tower_bridge.py', 'README.md', '.gitignore', '.gitattributes')]
for directory in ('Tower_Bridge', 'scene_components', 'assets', 'config', 'tests', 'docs', 'scripts', 'tools', '.github'):
    files.extend(sorted(p for p in (root / directory).rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts
                        and p.suffix not in ('.pyc', '.pyo') and not p.name.endswith('.blend1')
                        and not p.name.startswith(('preview', 'eevee_'))
                        and p.name != 'Tower_Bridge_Preview.mp4'))
archive = root / 'Tower_Bridge_Project.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
    for path in files:
        bundle.write(path, path.relative_to(root))
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    print('ARCHIVE_OK', len(bundle.namelist()), 'files', archive.stat().st_size, 'bytes')
