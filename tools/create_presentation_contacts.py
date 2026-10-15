"""Assemble encoded caption proof frames produced by inspect_presentation.py."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).resolve().parents[1];base=ROOT/'Tower_Bridge/extensions/presentation';meta=json.loads((base/'manifest.json').read_text(encoding='utf-8'));rows=meta['caption_frames'];sheet=Image.new('RGB',(1920,390*((len(rows)+2)//3)),(18,25,32));d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
for i,(start,end,text) in enumerate(rows):
    with Image.open(ROOT/'research/presentation_review'/f'{i:02d}.png') as im:sheet.paste(im.convert('RGB'),(i%3*640,i//3*390+30))
    d.text((i%3*640+8,i//3*390+5),f'{start:04d}-{end-1:04d} | {text}',font=font,fill='white')
sheet.save(base/'Contact_Sheet.jpg',quality=94)
