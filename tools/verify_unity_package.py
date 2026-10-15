"""Extract the Windows distribution and run its real hidden WARP self-check."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT/'Tower_Bridge_Unity_Windows.zip'
destination = Path(tempfile.mkdtemp(prefix='unity-portable-', dir=ROOT/'research'))
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    for entry in bundle.infolist():
        assert (destination/entry.filename).resolve().is_relative_to(destination.resolve())
    bundle.extractall(destination)
app = destination/'TowerBridge_Windows'
source_sha = hashlib.sha256((ROOT/'Tower_Bridge/Tower_Bridge.blend').read_bytes()).hexdigest()
export = json.loads((app/'TowerBridge_Data/StreamingAssets/scene.json').read_text(encoding='utf-8'))
assert export['source_sha256'] == source_sha
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
result = subprocess.run([str(app/'TowerBridge.exe'), '-force-d3d11', '-force-driver-type-warp',
                         '-screen-fullscreen','0','-screen-width','1280','-screen-height','720',
                         '-verifyRuntime','-logFile',str(app/'portable-runtime.log')],
                        cwd=app, startupinfo=startup, timeout=180)
assert result.returncode == 0, ('Portable Player failed',result.returncode)
runtime = json.loads((app/'runtime-verification.json').read_text(encoding='utf-8'))
assert runtime['passed'] and runtime['source_sha256'] == source_sha
images = {}
for name in ('runtime.png','runtime-river.png','runtime-evening.png','runtime-walk.png'):
    path = app/name
    with Image.open(path) as image:
        image.load()
        assert image.size == (1280,720)
        stats = ImageStat.Stat(image.convert('RGB'))
        assert max(stats.stddev) > 10 and max(stats.mean) > 15, ('Black/flat portable rendering',name)
    images[name] = hashlib.sha256(path.read_bytes()).hexdigest()
report = {'passed': True, 'archive_crc_check': True, 'extracted_player_executed': True,
          'source_sha256': source_sha, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'runtime_checks': runtime['checks'], 'images_sha256': images,
          'scope': 'Actual archive extracted into another directory, real Windows Player launched hidden on CPU WARP; runtime safety/walking/cameras and four nonblack renders pass. No hardware performance claim.'}
(ROOT/'Unity/Verification/portable-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('UNITY_PORTABLE_OK',json.dumps(report))
