"""Create explicitly labelled review proxies from complete final render frames."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scene_components.settings import load_config, frame_count
from scene_components.render_manifest import sha, make_identity, check_frames, png_size


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-cache',type=Path)
    args=parser.parse_args()
    cfg=load_config()
    count=frame_count(cfg)
    candidates=[args.source_cache] if args.source_cache else sorted((ROOT/'research/render_runs').glob('*'))
    valid=[]
    for directory in candidates:
        path=directory/'manifest.json'
        if not path.is_file():continue
        identity=json.loads(path.read_text(encoding='utf-8'))
        if identity.get('profile')!='final':continue
        expected=make_identity(ROOT/'Tower_Bridge/Tower_Bridge.blend',ROOT/'config/scene.json',ROOT/'render_tower_bridge.py','final',identity['blender_version'])
        expected['manifest_implementation_sha256']=sha(ROOT/'scene_components/render_manifest.py')
        if identity==expected:valid.append((directory,identity))
    if len(valid)!=1:raise ValueError(f'Expected exactly one compatible final cache, found {len(valid)}; pass --source-cache')
    source,identity=valid[0]
    check_frames(source,count,identity['size'])
    scale=cfg['render']['preview_scale']
    size=[cfg['render']['width']*scale//100,cfg['render']['height']*scale//100]
    manifest={'profile':'review_proxy','method':'downsample_final','filter':'Pillow LANCZOS',
              'source_identity':identity,'frames':count,'fps':cfg['fps'],'size':size,
              'scope':'Review proxy downsampled from final rendered frames; not a separate low-sample render.'}
    key=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:20]
    target=ROOT/'research/review_proxy'/key
    target.mkdir(parents=True,exist_ok=True)
    records={}
    for frame in range(1,count+1):
        original=source/f'{frame:04d}.png'
        destination=target/f'{frame:04d}.png'
        with Image.open(original) as image:
            image.resize(tuple(size),Image.Resampling.LANCZOS).save(destination,format='PNG')
        assert png_size(destination)==size
        records[destination.name]={'source_sha256':sha(original),'proxy_sha256':sha(destination)}
    manifest['images']=records
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('REVIEW_PROXY_READY',str(target),json.dumps({key:manifest[key] for key in ('profile','method','frames','fps','size')}))


if __name__=='__main__':main()
