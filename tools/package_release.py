"""Package only a complete release verified against the current source scene."""
from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parent.parent
out = root / 'Tower_Bridge'
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
assert count == 1440 and size == [1920, 1080], 'Release requires 60 seconds at 24 fps, Full HD'
assert video['frames'] == count and video['size'] == size and abs(video['fps'] - cfg['fps']) < .001
assert video['identity']['scene_sha256'] == sha(out / 'Tower_Bridge.blend'), 'Scene changed after encoding'
assert video['identity']['config_sha256'] == sha(root / 'config' / 'scene.json'), 'Configuration changed after encoding'
assert video['identity']['profile'] == 'final'
assert sha(out / 'Tower_Bridge_Animation.mp4') == video['video_sha256'], 'Video hash mismatch'
assert (out / 'Tower_Bridge_Animation.mp4').stat().st_size == video['bytes']
assert len(video.get('decoded_frames', [])) >= 7, 'Run VideoCheck before packaging'
for name in ('Open', 'Closed', 'City', 'Water', 'Evening'):
    assert (out / 'renders' / f'Tower_Bridge_{name}.png').is_file(), f'Missing {name} still'
assert (out / 'validation.json').is_file(), 'Run validation before packaging'
files = [root / name for name in ('build_tower_bridge.py', 'render_tower_bridge.py', 'README.md', '.gitignore', '.gitattributes')]
for directory in ('Tower_Bridge', 'scene_components', 'config', 'tests', 'docs', 'scripts', 'tools', '.github'):
    files.extend(sorted(p for p in (root / directory).rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts
                        and p.suffix not in ('.pyc', '.pyo') and not p.name.endswith('.blend1')))
archive = root / 'Tower_Bridge_Project.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
    for path in files:
        bundle.write(path, path.relative_to(root))
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    print('ARCHIVE_OK', len(bundle.namelist()), 'files', archive.stat().st_size, 'bytes')
