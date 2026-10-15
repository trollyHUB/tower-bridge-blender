"""Decode the actual MP4 AAC soundtrack through Blender/Audaspace and verify its PCM signal."""
import argparse,hashlib,json,sys,wave,time
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--video',type=Path,default=ROOT/'Tower_Bridge/extensions/presentation/Tower_Bridge_Titled_Sound.mp4');a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);video=a.video.resolve();identity=hashlib.sha256(video.read_bytes()).hexdigest();meta=json.loads((video.parent/'manifest.json').read_text());fps=meta['fps'];count=meta['frames'];duration=count/fps
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.fps=fps;s.frame_start=1;s.frame_end=count;strip=s.sequence_editor_create().strips.new_sound('Decode actual encoded MP4 AAC',str(video),channel=1,frame_start=1);assert Path(strip.sound.filepath).resolve()==video
out=ROOT/'research/audio_decode'/identity[:16];out.mkdir(parents=True,exist_ok=True);wav=out/'decoded_mp4_aac.wav';wav.unlink(missing_ok=True);bpy.ops.sound.mixdown(filepath=str(wav),check_existing=False,container='WAV',codec='PCM',format='S16',channels='STEREO',mixrate=48000,split_channels=False)
deadline=time.monotonic()+60
while not wav.exists() or wav.stat().st_size<round(duration*48000)*4+44:
    if time.monotonic()>deadline:raise TimeoutError('Encoded AAC mixdown did not finish')
    time.sleep(.1)
time.sleep(.2)
with wave.open(str(wav)) as w:
    rate=w.getframerate();channels=w.getnchannels();width=w.getsampwidth();frames=w.getnframes();signal=np.frombuffer(w.readframes(frames),dtype='<i2').astype(float).reshape(-1,channels)/32768
assert rate==48000 and channels==2 and width==2
rms=float(np.sqrt(np.mean(signal**2)));peak=float(np.max(np.abs(signal)));assert abs(frames/rate-duration)<.05 and .001<rms<.25 and peak<.99
mono=signal.mean(axis=1);bell_start=duration*8/60;window=min(1.,duration*.4);bell=mono[round(bell_start*rate):round((bell_start+window)*rate)];quiet=mono[round(duration*.7*rate):round(duration*.8*rate)];bell_rms=float(np.sqrt(np.mean(bell**2)));quiet_rms=float(np.sqrt(np.mean(quiet**2)));assert bell_rms>quiet_rms*1.3,(bell_rms,quiet_rms)
spectrum=np.abs(np.fft.rfft(bell*np.hanning(len(bell))));frequency=np.fft.rfftfreq(len(bell),1/rate);tones={}
for tone in (660,991):
    band=spectrum[np.abs(frequency-tone)<3];neighbours=spectrum[(np.abs(frequency-tone)>8)&(np.abs(frequency-tone)<35)];ratio=float(np.max(band)/max(float(np.median(neighbours)),1e-12));assert ratio>5,(tone,ratio);tones[str(tone)]=ratio
assert hashlib.sha256(video.read_bytes()).hexdigest()==identity
report={'passed':True,'source_scene_sha256':meta.get('source_scene_sha256'),'video_sha256':identity,'decoded_pcm_sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),'sample_rate':rate,'channels':channels,'sample_width_bytes':width,'sample_frames':frames,'seconds':frames/rate,'expected_seconds':duration,'rms':rms,'peak':peak,'bell_rms':bell_rms,'quiet_rms':quiet_rms,'bell_tone_peak_to_neighbour_median':tones,'scope':'Actual encoded MP4 AAC loaded as the sole VSE sound strip and mixed down through Blender/Audaspace to48kHz stereo PCM16. Duration, nonzero RMS, no clipping and warning-bell spectrum/window energy checked; DSP validation, not expert listening.'}
(video.parent/'audio_decode_validation.json').write_text(json.dumps(report,indent=2));print(report)
