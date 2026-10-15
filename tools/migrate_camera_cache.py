"""Reuse only certified unaffected PNGs after a narrow Camera09 correction.

python tools/migrate_camera_cache.py --old-cache research/render_runs/OLD
Requires a complete old cache, exact camera proof and current scene/tool/config.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scene_components.render_manifest import sha,make_identity,cache_directory,png_size

def certified_identity(proof,old,current,patch_sha):
    if proof.get('passed') is not True:raise ValueError('Camera proof did not pass')
    if proof['patch_implementation_sha256']!=patch_sha:raise ValueError('Camera proof tool changed')
    if proof['identity_before']!=old:raise ValueError('Old cache identity differs from certified baseline')
    if old['scene_sha256']!=proof['old_scene_sha256']:raise ValueError('Uncertified old scene')
    if current['scene_sha256']!=proof['new_scene_sha256']:raise ValueError('Uncertified current scene')
    expected=dict(old,scene_sha256=current['scene_sha256'])
    if current!=expected:raise ValueError('Renderer/config/helper/version/profile differs; reuse forbidden')
    # A claimed fingerprint must match its entire per-datablock record.
    import hashlib
    digest=hashlib.sha256(json.dumps(proof['normalized_datablocks'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if digest!=proof['normalized_fingerprint_sha256']:raise ValueError('Fingerprint proof mismatch')
    affected=proof['affected_frames']
    if not affected or affected!=list(range(min(affected),max(affected)+1)):raise ValueError('Invalid affected interval')
    if min(affected)<1 or max(affected)>current['frames']:raise ValueError('Affected interval outside scene')
    if proof['camera']!='09 | Bus stop camera':raise ValueError('Unexpected camera')
    return expected

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--old-cache',type=Path,required=True)
    args=parser.parse_args();oldcache=args.old_cache.resolve()
    assert oldcache.parent==(ROOT/'research/render_runs').resolve(),'Old cache must be project render cache'
    archive=ROOT/'research/before_bus_camera_fix';proof=json.loads((archive/'proof.json').read_text())
    assert sha(archive/'Tower_Bridge.blend')==proof['old_scene_sha256'],'Backup scene changed'
    old=json.loads((oldcache/'manifest.json').read_text())
    current=make_identity(ROOT/'Tower_Bridge/Tower_Bridge.blend',ROOT/'config/scene.json',ROOT/'render_tower_bridge.py','final',old['blender_version'])
    current['manifest_implementation_sha256']=sha(ROOT/'scene_components/render_manifest.py')
    identity=certified_identity(proof,old,current,sha(ROOT/'tools/patch_bus_camera.py'))
    # Complete old job first: do not certify an in-progress or partial cache.
    source_hashes={}
    for f in range(1,old['frames']+1):
        path=oldcache/f'{f:04d}.png'
        assert png_size(path)==old['size'],('Bad baseline PNG',f)
        source_hashes[f]=sha(path)
    newcache=cache_directory(ROOT/'research/render_runs',identity)
    assert newcache!=oldcache
    affected=set(proof['affected_frames']);copied={}
    for f in range(1,old['frames']+1):
        target=newcache/f'{f:04d}.png'
        if f in affected:
            assert not target.exists(),('Affected PNG already exists; use fresh target cache',f)
            continue
        source=oldcache/target.name
        assert sha(source)==source_hashes[f],('Old cache changed during migration',f)
        if target.exists():assert sha(target)==source_hashes[f],('Different target PNG',f)
        else:shutil.copy2(source,target)
        assert sha(target)==source_hashes[f],('Copy hash mismatch',f)
        copied[target.name]=source_hashes[f]
    report={'passed':True,'proof_sha256':sha(archive/'proof.json'),'source_cache':str(oldcache),'target_cache':str(newcache),
            'source_identity':old,'target_identity':identity,'excluded_frames':sorted(affected),'copied_png_sha256':copied,
            'scope':'Every old PNG CRC/decompression/dimensions checked, each copied PNG SHA256 matches baseline; affected camera interval excluded. Only scene hash changed in cache identity; exact config, renderer and manifest helper required.'}
    (newcache/'camera_reuse.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('CERTIFIED_CAMERA_CACHE_REUSE',newcache,'copied',len(copied),'rerender',len(affected))

if __name__=='__main__':main()
