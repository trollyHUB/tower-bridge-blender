"""Record checked still files immediately after a successful fresh Stills run."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scene_components.render_manifest import png_size
out=ROOT/'Tower_Bridge'
cfg=json.loads((ROOT/'config/scene.json').read_text(encoding='utf-8'))
size=[cfg['render']['width'],cfg['render']['height']]
images={}
for name in ['Open','Closed','City','Water','Evening','Detail']:
    path=out/'renders'/f'Tower_Bridge_{name}.png'
    assert png_size(path)==size, ('Invalid still',name)
    images[path.name]={'size':size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
report={'passed':True,'scene_sha256':hashlib.sha256((out/'Tower_Bridge.blend').read_bytes()).hexdigest(),'images':images}
(out/'stills_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('STILLS_VERIFIED',len(images))
