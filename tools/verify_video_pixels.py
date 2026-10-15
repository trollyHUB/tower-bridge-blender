"""Compare every decoded movie frame with its source and prepare review sheets.

The 8/255 RGB mean-error threshold detects major decoding/colour/frame errors
at the small decode size. It is not an exact-pixel or small-object motion proof.
"""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scene_components.render_manifest import sha,cache_directory
out=ROOT/'Tower_Bridge';report=json.loads((out/'full_video_validation.json').read_text(encoding='utf-8'))
assert report['passed'] and report['scene_sha256']==sha(out/'Tower_Bridge.blend')
assert report['video_sha256']==sha(out/'Tower_Bridge_Animation.mp4')
identity=report['identity'];source=cache_directory(ROOT/'research/render_runs',identity)
decoded=ROOT/'research/full_decode'/report['video_sha256'][:16]
target=ROOT/'research/visual_review';target.mkdir(parents=True,exist_ok=True)
try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
except OSError:font=ImageFont.load_default()
errors=[];pages=[]
for first in range(1,report['frames']+1,96):
    last=min(first+95,report['frames']);sheet=Image.new('RGB',(1920,1896),(15,22,31));draw=ImageDraw.Draw(sheet)
    for index,frame in enumerate(range(first,last+1)):
        with Image.open(decoded/f'frame_{frame:06d}.png') as im:actual=im.convert('RGB')
        with Image.open(source/f'{frame:04d}.png') as im:expected=im.convert('RGB').resize(actual.size,Image.Resampling.LANCZOS)
        error=float(np.abs(np.asarray(actual,dtype=np.float32)-np.asarray(expected,dtype=np.float32)).mean());errors.append(error)
        x=index%8*240;y=index//8*158
        sheet.paste(actual.resize((240,135),Image.Resampling.LANCZOS),(x,y+22))
        draw.text((x+4,y+3),f'{frame:04d} / {(frame-1)/report["fps"]:.2f}s',font=font,fill='white')
    path=target/f'encoded_{first:04d}_{last:04d}.jpg';sheet.save(path,quality=93)
    pages.append({'first':first,'last':last,'file':path.name,'sha256':sha(path)})
worst=int(np.argmax(errors))+1
result={'passed':max(errors)<=8,'frames_checked':len(errors),'decode_size':report['decode_size'],
        'mean_rgb_error_255':float(np.mean(errors)),'p95_rgb_error_255':float(np.percentile(errors,95)),
        'maximum_rgb_error_255':max(errors),'worst_frame':worst,'threshold_rgb_error_255':8,
        'scene_sha256':report['scene_sha256'],'video_sha256':report['video_sha256'],'identity':identity,
        'visual_contact_pages':pages,
        'scope':'Every decoded frame compared to Lanczos-downsampled render source at decode resolution. Global RGB mean absolute error threshold 8/255; not exact full-resolution fidelity or small-object motion proof. Contact pages are generated for separate visual review.'}
(out/'video_pixel_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('identity','visual_contact_pages')},indent=2))
assert result['passed'],('Video/source pixels disagree',worst,max(errors))
