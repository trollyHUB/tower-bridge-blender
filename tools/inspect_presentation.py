"""Decode actual encoded presentation captions at useful review sizes."""
import bpy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];base=ROOT/'Tower_Bridge/extensions/presentation';meta=json.loads((base/'manifest.json').read_text());video=base/'Tower_Bridge_Titled_Sound.mp4';frames=ROOT/'research/presentation_review';frames.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.resolution_percentage=100;s.render.fps=meta['fps'];s.render.use_sequencer=True;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='Standard';strip=s.sequence_editor_create().strips.new_movie('Actual encoded captions',str(video),channel=1,frame_start=1)
for i,(start,end,text) in enumerate(meta['caption_frames']):
    if end<=start:continue
    s.render.resolution_x=640;s.render.resolution_y=360;strip.transform.scale_x=640/meta['size'][0];strip.transform.scale_y=360/meta['size'][1];s.frame_set((start+end-1)//2);s.render.filepath=str(frames/f'{i:02d}.png');bpy.ops.render.render(write_still=True)
s.render.resolution_x,s.render.resolution_y=meta['size'];strip.transform.scale_x=1;strip.transform.scale_y=1;bus=next((r for r in meta['caption_frames'] if 'автобуса' in r[2]),meta['caption_frames'][0]);s.frame_set(378 if bus[0]<=378<bus[1] else (bus[0]+bus[1]-1)//2);s.render.filepath=str(base/'Title_Frame.png');bpy.ops.render.render(write_still=True)
