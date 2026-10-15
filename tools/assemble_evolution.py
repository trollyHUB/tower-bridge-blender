"""Compare the archived v0.1.0 image with the final city overview."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
baseline=ROOT/'assets/history/v0.1.0_Open.png'
current=ROOT/'Tower_Bridge/renders/Tower_Bridge_Open.png'
canvas=Image.new('RGB',(2400,765),(20,29,42));draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',30)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
for col,(path,label) in enumerate([(baseline,'БЫЛО — исходная диорама v0.1.0'),(current,'СТАЛО — живая сцена v1.1.0')]):
    draw.text((col*1200+20,12),label,font=font,fill='white')
    with Image.open(path) as source:canvas.paste(source.convert('RGB').resize((1200,675),Image.Resampling.LANCZOS),(col*1200,55))
draw.text((20,737),'Архивный и итоговый общие виды: композиция и масштаб ракурсов отличаются.',font=small,fill=(200,216,234))
target=ROOT/'Tower_Bridge/renders/Project_Evolution.jpg';canvas.save(target,quality=95)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
report={'passed':True,'baseline_git_tag':'v0.1.0','baseline_git_path':'Tower_Bridge/renders/Tower_Bridge_Open.png',
        'baseline_image_sha256':sha(baseline),'current_image_sha256':sha(current),
        'current_scene_sha256':sha(ROOT/'Tower_Bridge/Tower_Bridge.blend'),'comparison_sha256':sha(target),
        'scope':'Original archived and current unretouched renders, resized with labels only. Camera composition differs. Matched cameras for v1.0.0 versus v1.1.0 are in Before_After.jpg.'}
(ROOT/'Tower_Bridge/evolution_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(target)
