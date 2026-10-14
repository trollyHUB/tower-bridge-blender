"""Package the verified project for a GitHub release, excluding local work files."""
from pathlib import Path
import json
import zipfile

root = Path(__file__).resolve().parent.parent
out = root / 'Tower_Bridge'
video = json.loads((out / 'video_validation.json').read_text(encoding='utf-8'))
assert video['frames'] == 720 and video['size'] == [1280, 720]
assert (out / 'Tower_Bridge_Animation.mp4').stat().st_size == video['bytes']

files = [root / name for name in (
    'build_tower_bridge.py', 'render_tower_bridge.py', 'README.md',
    '.gitignore', '.gitattributes',
)]
for directory in ('Tower_Bridge', 'docs', 'scripts', 'tools', '.github'):
    files.extend(sorted(
        p for p in (root / directory).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts
        and p.suffix not in ('.pyc', '.pyo') and not p.name.endswith('.blend1')
    ))
assert len(list((out / 'renders').glob('*.png'))) == 3
archive = root / 'Tower_Bridge_Project.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
    for path in files:
        bundle.write(path, path.relative_to(root))
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    print('ARCHIVE_OK', len(bundle.namelist()), 'files', archive.stat().st_size, 'bytes')
