"""Assemble unretouched matched-camera renders with explicit version labels."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',32)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
canvas=Image.new('RGB',(2400,4*735+70),(20,29,42));draw=ImageDraw.Draw(canvas)
draw.text((30,16),'БЫЛО — v1.0.0',font=font,fill='white');draw.text((1230,16),'СТАЛО — v1.1.0',font=font,fill='white')
for row,(key,title) in enumerate([('social','Пассажиры, кафе и уличная жизнь'),('river','Волны, плавучесть и след судов'),('architecture','Отделка башен, материалы и общий ветер'),('evening','Фонари, фары и архитектурное освещение')]):
    y=70+row*735
    for col,version in enumerate(['before','after']):
        with Image.open(ROOT/f'research/comparison/{version}_{key}.png') as im:canvas.paste(im.convert('RGB'),(col*1200,y+45))
    draw.text((30,y+5),title,font=small,fill=(200,216,234))
target=ROOT/'Tower_Bridge/renders/Before_After.jpg';canvas.save(target,quality=94)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
report={'passed':True,'before_version':'v1.0.0','after_version':'v1.1.0',
        'before_scene_sha256':sha(ROOT/'research/before_v1/Tower_Bridge.blend'),
        'after_scene_sha256':sha(ROOT/'Tower_Bridge/Tower_Bridge.blend'),
        'comparison_sha256':sha(target),'matched_camera_views':['social','river','architecture','evening'],
        'scope':'Matched camera poses, scale, frame references and render settings. Labels and assembly only; renders are unretouched.'}
(ROOT/'Tower_Bridge/comparison_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(target)
