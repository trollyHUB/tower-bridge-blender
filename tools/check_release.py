"""Extract and open a complete release in another directory without saving it."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
import argparse

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--blender',default=r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
args=parser.parse_args()
(ROOT/'research').mkdir(exist_ok=True)
destination=Path(tempfile.mkdtemp(prefix='portable-release-',dir=ROOT/'research'))
with zipfile.ZipFile(ROOT/'Tower_Bridge_Project.zip') as archive:
    assert archive.testzip() is None
    for entry in archive.infolist():
        target=(destination/entry.filename).resolve()
        assert target.is_relative_to(destination.resolve()), 'Unsafe archive path'
    archive.extractall(destination)
scene=destination/'Tower_Bridge/Tower_Bridge.blend'
assert hashlib.sha256(scene.read_bytes()).digest()==hashlib.sha256((ROOT/'Tower_Bridge/Tower_Bridge.blend').read_bytes()).digest()
check=destination/'check_open.py'
check.write_text('''import bpy, json
from pathlib import Path
s=bpy.context.scene
assert s.frame_start==1 and s.frame_end==1440 and s.render.fps==24
assert all(i.source!='FILE' or i.packed_file for i in bpy.data.images)
assert len([o for o in s.objects if o.get('actor_type')=='vehicle'])==14
for f in [1,432,720,1056,1440]:
    s.frame_set(f)
    bpy.context.view_layer.update()
print('PORTABLE_SCENE_OK',len(s.objects))
''',encoding='utf-8')
result=subprocess.run([args.blender,'--background',str(scene),'--python-exit-code','1','--python',str(check)],capture_output=True,text=True,encoding='utf-8',errors='replace')
(ROOT/'research/portable-release-check.log').write_text(result.stdout+result.stderr,encoding='utf-8')
assert result.returncode==0 and 'PORTABLE_SCENE_OK' in result.stdout, result.stdout[-2000:]
report={'passed':True,'extracted_scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest(),
        'checked_frames':[1,432,720,1056,1440],'external_textures_missing':False,
        'archive_crc_check':True}
(ROOT/'Tower_Bridge/portable_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PORTABLE_RELEASE_OK',json.dumps(report))
