"""Compare all decoded loop frames and produce a small decoded contact sheet."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def main():
    base=ROOT/'Tower_Bridge/extensions/day_loop';manifest=json.loads((base/'manifest.json').read_text());directory=ROOT/'research/extension_decode'/manifest['video_sha256'][:16];frames=ROOT/'research/day_loop_frames'/manifest['source_sha256'][:12]
    def pix(f):return np.asarray(Image.open(directory/f'{f:04d}.png').convert('RGB'),dtype=float)
    def diff(a,b):return float(np.abs(a-b).mean())
    wrap=diff(pix(240),pix(1));internal=(diff(pix(1),pix(2))+diff(pix(239),pix(240)))/2;errors=[]
    for f in range(1,241):
        expected=np.asarray(Image.open(frames/f'{f:04d}.png').convert('RGB').resize((192,108),Image.Resampling.LANCZOS),dtype=float);errors.append(diff(pix(f),expected))
    sheet=Image.new('RGB',(960,486),(18,25,32));d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    for i,f in enumerate((1,2,25,49,73,97,121,145,169,193,239,240)):
        im=Image.open(directory/f'{f:04d}.png').convert('RGB').resize((240,135));x=i%4*240;y=i//4*162;sheet.paste(im,(x,y+25));d.text((x+5,y+3),f'{f:04d} / {(f-1)/24:.2f}s',font=font,fill='white')
    review=base/'Contact_Sheet.jpg';review.parent.mkdir(parents=True,exist_ok=True);sheet.save(review,quality=93)
    report={'passed':max(errors)<8 and wrap>0 and wrap<3*internal,'source_scene_sha256':manifest['source_sha256'],'video_sha256':manifest['video_sha256'],'decoded_frames_compared':240,'mean_rgb_error_255':float(np.mean(errors)),'maximum_rgb_error_255':max(errors),'encoded_wrap_difference_255':wrap,'encoded_adjacent_difference_255':internal,'encoded_seam_ratio':wrap/internal,'contact_sheet':str(review.relative_to(ROOT)),'contact_sha256':hashlib.sha256(review.read_bytes()).hexdigest(),'scope':'All decoded 192x108 frames compared against downsampled source; global error threshold 8/255. Actual decoded wrap must be nonzero and less than three times adjacent internal differences.'}
    (base/'pixel_validation.json').write_text(json.dumps(report,indent=2));print(report);assert report['passed']
if __name__=='__main__':main()
