"""Package the E05 source prototype, explicitly excluding Editor caches/builds."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
files = []
for folder in ('Assets', 'Packages', 'ProjectSettings', 'Verification'):
    files.extend(p for p in (ROOT/'Unity'/folder).rglob('*') if p.is_file())
files.extend(ROOT/'Unity'/name for name in ('.gitignore', 'compile_sources.py', 'build_windows.ps1', 'record_verification.py', 'verification-status.json'))
files += [ROOT/'docs/UNITY.md', ROOT/'docs/REMAINING_WORK.md', ROOT/'tools/export_unity.py',
          ROOT/'tests/test_unity_export.py']
assert all(p.is_file() for p in files)
archive = ROOT/'Tower_Bridge_Unity_Source.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as out:
    for path in sorted(files):
        out.write(path, path.relative_to(ROOT))
with zipfile.ZipFile(archive) as out:
    assert out.testzip() is None
    assert not any(set(Path(n).parts) & {'Library','Temp','Logs','UserSettings','Build','Obj'} for n in out.namelist())
    status = json.loads(out.read('Unity/verification-status.json'))
    assert status['status'] == 'E05_VERIFIED'
    assert status['editor_passed'] and status['runtime_passed'] and status['walk_controls_passed']
print('UNITY_SOURCE_ARCHIVE_OK', len(files), archive.stat().st_size,
      hashlib.sha256(archive.read_bytes()).hexdigest(), 'Verified interactive prototype sources')
build = ROOT/'Unity/Build'
runtime = json.loads((build/'runtime-verification.json').read_text(encoding='utf-8'))
assert runtime['passed'] and runtime['source_sha256'] == status['source_sha256']
assert (build/'TowerBridge.exe').is_file()
app_archive = ROOT/'Tower_Bridge_Unity_Windows.zip'
with zipfile.ZipFile(app_archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as out:
    for path in sorted(p for p in build.rglob('*') if p.is_file() and p.suffix not in ('.log','.pdb','.mdb')):
        if any('DoNotShip' in part for part in path.parts):
            continue
        out.write(path, Path('TowerBridge_Windows')/path.relative_to(build))
    out.write(ROOT/'docs/UNITY.md', 'TowerBridge_Windows/UNITY.md')
    out.write(ROOT/'Unity/verification-status.json', 'TowerBridge_Windows/verification-status.json')
with zipfile.ZipFile(app_archive) as out:
    assert out.testzip() is None
    assert 'TowerBridge_Windows/TowerBridge.exe' in out.namelist()
print('UNITY_PLAYER_ARCHIVE_OK', app_archive.stat().st_size,
      hashlib.sha256(app_archive.read_bytes()).hexdigest())
