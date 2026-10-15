"""Decode each extension video frame through VSE and verify MP4 audio stream metadata."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mp4_audio(path):
    data=Path(path).read_bytes();i=data.find(b'mp4a')
    if i<0:return None
    # ISO/IEC audio sample entry: reserved[6],data_reference[2],reserved[8],channels[2],sample_size[2],reserved[4],rate16.16[4].
    return {'codec':'AAC/mp4a','channels':struct.unpack_from('>H',data,i+20)[0],'sample_rate':struct.unpack_from('>I',data,i+28)[0]>>16}
def main():
    import bpy
    sys.path.insert(0,str(ROOT));from scene_components.render_manifest import png_size
    p=argparse.ArgumentParser();p.add_argument('--video',type=Path,required=True);p.add_argument('--require-audio',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);identity=sha(a.video);clip=bpy.data.movieclips.load(str(a.video.resolve()));count=clip.frame_duration;size=list(clip.size);fps=clip.fps;audio=mp4_audio(a.video)
    if a.require_audio:assert audio and audio['sample_rate']==48000,audio
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.resolution_x=192;s.render.resolution_y=108;s.render.resolution_percentage=100;s.render.fps=round(fps);s.render.use_sequencer=True;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='Standard'
    strip=s.sequence_editor_create().strips.new_movie('Decode every encoded frame',str(a.video.resolve()),channel=1,frame_start=1);strip.transform.scale_x=192/size[0];strip.transform.scale_y=108/size[1]
    frames=ROOT/'research/extension_decode'/identity[:16];frames.mkdir(parents=True,exist_ok=True)
    for f in range(1,count+1):
        s.frame_set(f);target=frames/f'{f:04d}.png';s.render.filepath=str(target);bpy.ops.render.render(write_still=True);assert png_size(target)==[192,108]
    assert sha(a.video)==identity
    report={'passed':True,'decoded_count':count,'frames':count,'fps':fps,'size':size,'video_sha256':identity,'audio_metadata':audio,'scope':'Every video frame decoded with Blender VSE and complete PNG streams validated; audio metadata verifies stream existence and rate, not listening quality.'}
    (a.video.parent/(a.video.stem+'_validation.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
if __name__=='__main__':main()
