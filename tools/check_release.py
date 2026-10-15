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
check.write_text('''import bpy, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from scene_components.settings import load_config, frame_count
from scene_components.scenario import opening
import math
cfg=load_config(Path(__file__).parent/'config/scene.json')
count=frame_count(cfg)
s=bpy.context.scene
assert s.frame_start==1 and s.frame_end==count and s.render.fps==cfg['fps']
assert abs(s.render.fps_base-1.0)<1e-7
assert [s.render.resolution_x,s.render.resolution_y]==[cfg['render']['width'],cfg['render']['height']]
assert all(i.source!='FILE' or i.packed_file for i in bpy.data.images)
vehicles=[o for o in s.objects if o.get('actor_type')=='vehicle']
assert len(vehicles)==(14 if cfg['features'].get('traffic',True) else 0)
frames=sorted(set(max(1,round(count*t)) for t in (0,.3,.5,11/15,1)))
for f in frames:
    s.frame_set(f)
    bpy.context.view_layer.update()
    expected=opening(f)
    assert abs(bpy.data.objects['BRIDGE CONTROL | Opening degrees']['Opening degrees']-expected)<.001
    for label,sign in [('North',-1),('South',1)]:
        assert abs(bpy.data.objects[label+' bascule hinge'].rotation_euler.y-sign*math.radians(expected))<1e-5
print('PORTABLE_SCENE_OK',json.dumps({'objects':len(s.objects),'checked_frames':frames,'frames':count,'fps':cfg['fps'],'drivers_evaluated':True}))
''',encoding='utf-8')
result=subprocess.run([args.blender,'--background',str(scene),'--python-exit-code','1','--python',str(check)],capture_output=True,text=True,encoding='utf-8',errors='replace')
(ROOT/'research/portable-release-check.log').write_text(result.stdout+result.stderr,encoding='utf-8')
assert result.returncode==0 and 'PORTABLE_SCENE_OK' in result.stdout, result.stdout[-2000:]
portable=json.loads(next(line.split('PORTABLE_SCENE_OK ',1)[1] for line in result.stdout.splitlines() if line.startswith('PORTABLE_SCENE_OK ')))
report={'passed':True,'extracted_scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest(),
        'checked_frames':portable['checked_frames'],'frames':portable['frames'],'fps':portable['fps'],'external_textures_missing':False,
        'archive_crc_check':True,'animation_drivers_evaluated':portable['drivers_evaluated']}
(ROOT/'Tower_Bridge/portable_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PORTABLE_RELEASE_OK',json.dumps(report))
