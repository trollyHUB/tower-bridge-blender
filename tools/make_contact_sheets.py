"""Lay out every cached frame for sequential visual review, without retouching."""
import argparse,json,hashlib,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scene_components.settings import load_config,frame_count
from scene_components.render_manifest import sha,check_frames
parser=argparse.ArgumentParser();parser.add_argument('--profile',choices=['preview','final'],default='preview');args=parser.parse_args()
cfg=load_config();count=frame_count(cfg)
candidates=[]
for path in (ROOT/'research/render_runs').glob('*/manifest.json'):
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest['scene_sha256']==sha(ROOT/'Tower_Bridge/Tower_Bridge.blend') and manifest['profile']==args.profile and manifest['implementation_sha256']==sha(ROOT/'render_tower_bridge.py') and manifest['config_sha256']==sha(ROOT/'config/scene.json'):
        candidates.append((path.parent,manifest))
assert len(candidates)==1,('Expected one current render cache',len(candidates))
directory,identity=candidates[0];check_frames(directory,count,identity['size'])
target=ROOT/'research/visual_review';target.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
pages=[]
for first in range(1,count+1,96):
    end=min(count,first+95);sheet=Image.new('RGB',(1920,12*158),(15,22,31));draw=ImageDraw.Draw(sheet)
    for index,frame in enumerate(range(first,end+1)):
        x=index%8*240;y=index//8*158
        with Image.open(directory/f'{frame:04d}.png') as source:
            sheet.paste(source.convert('RGB').resize((240,135),Image.Resampling.LANCZOS),(x,y+22))
        draw.text((x+4,y+3),f'{frame:04d} / {(frame-1)/cfg["fps"]:.2f}s',font=font,fill='white')
    path=target/f'{args.profile}_{first:04d}_{end:04d}.jpg';sheet.save(path,quality=92)
    pages.append({'first':first,'last':end,'path':str(path.relative_to(ROOT)),'sha256':sha(path)})
report={'profile':args.profile,'identity':identity,'frames_in_sheets':count,'pages':pages,
        'scope':'Every rendered frame laid out in time order. Generation alone does not assert visual acceptance.'}
(target/f'{args.profile}_sheets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'frames':count,'pages':len(pages),'directory':str(target)}))
