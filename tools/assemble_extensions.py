"""Assemble a labelled overview from actual release renders and Player captures."""
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scene_components.render_manifest import sha

out = ROOT/'Tower_Bridge'
loop = json.loads((out/'extensions/day_loop/manifest.json').read_text(encoding='utf-8'))
items = [
    ('E01 • Автобус: остановка и двери',out/'renders/Tower_Bridge_Bus_Stop.png'),
    ('E04 • Пасмурная погода, малая плотность',out/'extensions/weather/Overcast_Sparse.png'),
    ('E03 • Отдельная дневная петля, 10 секунд',ROOT/'research/day_loop_frames'/loop['source_sha256'][:12]/'0001.png'),
    ('E05 • Прогулка в настоящем Unity Player',ROOT/'Unity/Verification/runtime-walk.png'),
]
canvas = Image.new('RGB',(1920,1220),(19,28,38))
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',30)
small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
records=[]
for i,(label,path) in enumerate(items):
    x,y=i%2*960,i//2*610
    with Image.open(path) as image:
        canvas.paste(image.convert('RGB').resize((960,540),Image.Resampling.LANCZOS),(x,y+48))
    draw.text((x+16,y+10),label,font=font,fill='white')
    records.append({'label':label,'source':str(path.relative_to(ROOT)),'sha256':sha(path)})
target=out/'renders/Extensions_v1.2.0.jpg'
canvas.save(target,quality=94)
manifest={'passed':True,'scene_sha256':sha(out/'Tower_Bridge.blend'),
          'inputs':records,'output_sha256':sha(target),
          'scope':'Actual Blender renders and actual Unity Player camera capture; compositions differ. E02 is supplied separately as titled sound video.'}
(out/'extensions_image_validation.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('EXTENSIONS_IMAGE_OK',target)
