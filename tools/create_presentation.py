"""Original procedural ambience and Russian captions; run with Blender -b --python FILE -- --input VIDEO."""
import argparse, hashlib, json, math, random, struct, sys, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
CAPTIONS=[(0,8,'Тауэрский мост • Лондон'),(8,14,'Предупреждение: подготовка к подъёму'),(14,18,'Шлагбаумы закрываются'),(18,26,'Подъём разводных пролётов'),(26,36,'Проход судна по Темзе'),(36,44,'Опускание пролётов'),(44,46,'Открытие шлагбаумов'),(46,50,'Движение возобновляется'),(50,60,'Вечер над Темзой')]

def caption_frames(count,config=None):
    """Half-open frame intervals; bus mask matches the configured camera cuts exactly."""
    from scene_components.settings import load_config
    from scene_components.traffic import bus_stop_times
    config=load_config() if config is None else config
    rows=[(round(start/60*count)+1,round(end/60*count)+1,text) for start,end,text in CAPTIONS]
    if not config['features'].get('traffic',True) or not config['traffic'].get('bus_stop',True):return rows
    _,arrival,departure,_=bus_stop_times(config['traffic']['speed'])
    bus_start=max(1,round((arrival-2.5)*count/1440))
    bus_end=min(count,math.ceil((departure+5)*count/1440))
    result=[]
    for start,end,text in rows:
        cuts=sorted({start,end,*[x for x in (bus_start,bus_end) if start<x<end]})
        for left,right in zip(cuts,cuts[1:]):
            label='Короткая остановка автобуса' if bus_start<=left<bus_end else text
            if result and result[-1][1]==left and result[-1][2]==label:result[-1]=(result[-1][0],right,label)
            else:result.append((left,right,label))
    return result
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def synthesize(path,seconds,rate=24000):
    rng=random.Random(1894); low=0.; samples=[]
    for i in range(round(seconds*rate)):
        t=i/rate; low=.985*low+.015*rng.uniform(-1,1)
        river=.035*rng.uniform(-1,1); wind=.24*low*(.7+.3*math.sin(t*.47)**2)
        traffic=.018*math.sin(2*math.pi*63*t)*(.5+.5*math.sin(t*.31)**2)
        bell=0.
        for strike in (seconds*8/60,seconds*10/60,seconds*14/60):
            age=t-strike
            if 0<=age<4: bell+=.11*math.exp(-age*1.8)*(math.sin(2*math.pi*660*age)+.35*math.sin(2*math.pi*991*age))
        fade=min(1,t/1.5,(seconds-t)/1.5)
        samples.append(struct.pack('<h',round(32767*max(-1,min(1,(river+wind+traffic+bell)*fade)))))
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as out: out.setparams((1,2,rate,0,'NONE','not compressed'));out.writeframes(b''.join(samples))
def main():
    import bpy
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=ROOT/'Tower_Bridge/Tower_Bridge_Animation.mp4');p.add_argument('--output',type=Path,default=ROOT/'Tower_Bridge/extensions/presentation/Tower_Bridge_Titled_Sound.mp4');p.add_argument('--audio-output',type=Path,default=ROOT/'assets/audio/tower_bridge_original.wav');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.input=a.input.resolve();a.output=a.output.resolve();source_hash=sha(a.input); clip=bpy.data.movieclips.load(str(a.input));fps=round(clip.fps);count=clip.frame_duration;seconds=count/fps;size=list(clip.size)
    from scene_components.settings import load_config
    config=load_config();captions=caption_frames(count,config)
    audio=a.audio_output.resolve();synthesize(audio,seconds)
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.fps=fps;s.frame_start=1;s.frame_end=count;s.render.resolution_x,s.render.resolution_y=size;s.render.resolution_percentage=100;s.view_settings.view_transform='Standard';ed=s.sequence_editor_create();seq=ed.strips
    seq.new_movie('Final silent source',str(a.input),channel=1,frame_start=1);seq.new_sound('Original synthesized ambience',str(audio),channel=2,frame_start=1)
    font=Path('C:/Windows/Fonts/arial.ttf')
    for start,end,text in captions:
        if end<=start:continue
        strip=seq.new_effect(text,type='TEXT',channel=3,frame_start=start,length=end-start)
        strip.text=text;strip.font_size=max(8,round(44*size[1]/1080));strip.location=(.5,.075);strip.color=(1,1,1,1);strip.use_shadow=True
        if font.exists():strip.font=bpy.data.fonts.load(str(font))
    a.output.parent.mkdir(parents=True,exist_ok=True);s.render.use_sequencer=True
    s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG';s.render.ffmpeg.format='MPEG4';s.render.ffmpeg.codec='H264';s.render.ffmpeg.audio_codec='AAC';s.render.ffmpeg.audio_mixrate=48000;s.render.ffmpeg.constant_rate_factor='HIGH';s.render.filepath=str(a.output)
    bpy.ops.render.render(animation=True)
    assert sha(a.input)==source_hash
    report={'passed':True,'source_sha256':source_hash,'output_sha256':sha(a.output),'audio_sha256':sha(audio),'tool_sha256':sha(__file__),'frames':count,'fps':fps,'size':size,'caption_frames':captions,'caption_reference_seconds':CAPTIONS,'caption_config':{'traffic_speed':config['traffic']['speed'],'bus_stop':config['traffic'].get('bus_stop',True),'config_sha256':sha(ROOT/'config/scene.json')},'audio':{'original':True,'channels':1,'sample_rate':24000,'sources':['seeded noise river and wind','63 Hz distant traffic','660/991 Hz decaying bell']}}
    (a.output.parent/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
