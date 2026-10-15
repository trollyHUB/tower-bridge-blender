"""Run the real core pipeline in an isolated alternate configuration on two CPU threads."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--blender',default=r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe');args=parser.parse_args()
    dest=ROOT/'research/config_smoke_v1_2';dest.mkdir(parents=True,exist_ok=True)
    if (dest/'Tower_Bridge/Tower_Bridge.blend').exists():raise RuntimeError('Existing smoke output: preserve or remove explicitly before rerunning')
    source=[]
    for name in ('build_tower_bridge.py','render_tower_bridge.py','README.md','.gitignore','.gitattributes','requirements-dev.txt'):
        shutil.copy2(ROOT/name,dest/name);source.append(name)
    for directory in ('scene_components','config','tools','scripts','docs','assets','tests','.github'):
        shutil.copytree(ROOT/directory,dest/directory,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        source += [p.relative_to(ROOT).as_posix() for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    hashes={name:sha(ROOT/name) for name in sorted(source)}
    cfg=json.loads((dest/'config/scene.json').read_text(encoding='utf-8-sig'));cfg.update(fps=12,duration_seconds=10)
    cfg['render'].update(width=320,height=180,preview_scale=50,samples=1,preview_samples=1,still_samples=1,device='cpu',engine='CYCLES')
    cfg['traffic'].update(vehicles_per_direction=5,speed=20,stop_line=60,minimum_gap=3);cfg['people']['bank_walkers']=4;cfg['weather']['preset']='overcast';cfg['lighting']['mode']='day'
    (dest/'config/scene.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
    output=dest/'Tower_Bridge';output.mkdir(exist_ok=True)
    for name in ('НАЧНИТЕ ЗДЕСЬ.txt','SOURCES.txt'):shutil.copy2(ROOT/'Tower_Bridge'/name,output/name)
    logs=dest/'research/smoke_logs';logs.mkdir(parents=True,exist_ok=True);results=[]
    env=os.environ.copy();env.pop('TOWER_BRIDGE_CONFIG',None);env.pop('TOWER_BRIDGE_OUTPUT',None);env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
    def run(label,cmd,success=True):
        started=time.perf_counter();p=subprocess.run(cmd,cwd=dest,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace');elapsed=time.perf_counter()-started
        (logs/(label+'.log')).write_text(p.stdout,encoding='utf-8');results.append(dict(action=label,command=cmd,returncode=p.returncode,seconds=round(elapsed,3),expected_success=success))
        print(label,p.returncode,round(elapsed,2),flush=True)
        if (p.returncode==0)!=success:raise RuntimeError(label+' unexpected result: '+p.stdout[-2500:])
    def blender(label,script,*tail):run(label,[args.blender,'--background','--threads','2','--python-exit-code','1','--python',str(dest/script),*tail])
    test_code="import unittest; from pathlib import Path; names=[p.name for p in Path('tests').glob('test_*.py') if p.stem not in ('test_unity_export','test_media_extensions')]; suite=unittest.TestSuite(unittest.defaultTestLoader.discover('tests',pattern=n) for n in names); r=unittest.TextTestRunner().run(suite); raise SystemExit(not r.wasSuccessful())"
    run('core_unit_tests',[sys.executable,'-c',test_code])
    blender('Build','build_tower_bridge.py')
    for action in ('finalize','validate','preview','preview_encode','animation','encode','video_check'):
        blender(action,'render_tower_bridge.py','--',action)
    blender('full_decode','tools/check_video_full.py');blender('stills','render_tower_bridge.py','--','stills')
    run('verify_stills',[sys.executable,'tools/verify_stills.py'])
    full=output/'full_video_validation.json';original=full.read_text();full.unlink()
    run('reject_missing_full_decode',[sys.executable,'tools/package_release.py','--core-only'],False)
    stale=json.loads(original);stale['video_sha256']='0'*64;full.write_text(json.dumps(stale))
    run('reject_stale_full_decode',[sys.executable,'tools/package_release.py','--core-only'],False);full.write_text(original)
    run('package',[sys.executable,'tools/package_release.py','--core-only'])
    run('portable_open',[sys.executable,'tools/check_release.py','--blender',args.blender])
    blender('cpu_diagnostics','tools/diagnose_scene.py')
    changed=[name for name,value in hashes.items() if sha(ROOT/name)!=value]
    report=dict(passed=True,version='1.2.0',configuration=cfg,source_sha256=hashes,source_changed_after_snapshot=changed,isolated_root=str(dest),commands=results,scope='Actual complete core CPU pipeline, preview and final encoding, complete video decode integrity, six stills and portable scene opening. Does not establish visual correctness of every frame or optional extensions/Unity.',threads=2)
    target=ROOT/'Tower_Bridge/configuration_validation.json';history=ROOT/'assets/history/v1.1.0';history.mkdir(parents=True,exist_ok=True)
    if target.exists() and not (history/'configuration_validation.json').exists():shutil.copy2(target,history/'configuration_validation.json')
    target.write_text(json.dumps(report,indent=2),encoding='utf-8');(output/'configuration_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('CONFIGURATION_SMOKE_OK',flush=True)
if __name__=='__main__':main()
