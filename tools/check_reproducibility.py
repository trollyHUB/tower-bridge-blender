"""CPU-only independent rebuild and semantic scene reproducibility check.

Run: blender --background --threads 2 --python tools/check_reproducibility.py
No render is performed and the primary .blend is never saved or changed.
"""
import array
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import bpy

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Tower_Bridge'
WORK=ROOT/'research'/'repro_smoke'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def coordinates(data):
    values=array.array('f',[0.])*(len(data)*3)
    data.foreach_get('co',values)
    return digest([round(v,6) for v in values])


def fingerprint(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene=bpy.context.scene;scene.cycles.device='CPU'
    objects=sorted((o for o in scene.objects if o.type!='CAMERA'),key=lambda o:o.name)
    cached={};records=[]
    for ob in objects:
        record={'name':ob.name,'type':ob.type,'parent':ob.parent.name if ob.parent else None}
        if ob.type=='MESH':
            mesh=ob.data
            if mesh.name not in cached:
                topology=digest([list(p.vertices) for p in mesh.polygons])
                keys=[]
                if mesh.shape_keys:
                    keys=[{'name':k.name,'coordinates_sha256':coordinates(k.data)} for k in mesh.shape_keys.key_blocks]
                cached[mesh.name]={'vertices':len(mesh.vertices),'faces':len(mesh.polygons),
                    'coordinates_sha256':coordinates(mesh.vertices),'topology_sha256':topology,
                    'materials':[m.name if m else None for m in mesh.materials],
                    'polygon_material_sha256':digest([p.material_index for p in mesh.polygons]),'shape_keys':keys}
            record['mesh']=cached[mesh.name]
        records.append(record)
    frames=sorted(set((1,round(scene.frame_end/4),round(scene.frame_end/2),scene.frame_end)))
    samples=[]
    for f in frames:
        scene.frame_set(f);bpy.context.view_layer.update()
        transforms=[(o.name,[round(v,6) for row in o.matrix_world for v in row]) for o in objects]
        samples.append({'frame':f,'world_matrices_sha256':digest(transforms)})
    config=json.loads(scene['Configuration'])
    result={'configuration_sha256':digest(config),'object_mesh_sha256':digest(records),
            'objects':len(objects),'unique_meshes':len(cached),'samples':samples}
    result['semantic_sha256']=digest(result)
    return result,records


def main():
    primary_file=OUT/'Tower_Bridge.blend'
    initial_file_sha=hashlib.sha256(primary_file.read_bytes()).hexdigest()
    WORK.mkdir(parents=True,exist_ok=True)
    if '--skip-build' not in sys.argv:
        shutil.copy2(ROOT/'build_tower_bridge.py',WORK/'build_tower_bridge.py')
        shutil.copytree(ROOT/'scene_components',WORK/'scene_components',dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ROOT/'config',WORK/'config',dirs_exist_ok=True)
        env=dict(os.environ);env['CUDA_VISIBLE_DEVICES']='-1';env['HIP_VISIBLE_DEVICES']='-1'
        command=[bpy.app.binary_path,'--background','--threads','2','--python-exit-code','1',
                 '--python',str(WORK/'build_tower_bridge.py')]
        with (WORK/'build.log').open('w',encoding='utf-8') as log:
            subprocess.run(command,cwd=WORK,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    primary,primary_records=fingerprint(OUT/'Tower_Bridge.blend')
    rebuilt,rebuilt_records=fingerprint(WORK/'Tower_Bridge'/'Tower_Bridge.blend')
    (WORK/'primary_fingerprint.json').write_text(json.dumps(primary,indent=2),encoding='utf-8')
    (WORK/'rebuilt_fingerprint.json').write_text(json.dumps(rebuilt,indent=2),encoding='utf-8')
    differences=[]
    a={r['name']:r for r in primary_records};b={r['name']:r for r in rebuilt_records}
    for name in sorted(a.keys()|b.keys()):
        if a.get(name)!=b.get(name):differences.append(name)
    assert hashlib.sha256(primary_file.read_bytes()).hexdigest()==initial_file_sha, 'Primary scene file changed during reproducibility run'
    report={'primary_file_sha256':initial_file_sha,'primary_file_unchanged':True,'passed':primary==rebuilt,'blender_version':bpy.app.version_string,'execution':'CPU only; no renders',
        'scope':'Same configuration and seed, independently rebuilt in research/repro_smoke. Sorted non-camera object names/types/parents; mesh topology, vertex coordinates, polygon material indices, material names, shape-key coordinates; world matrices at four frames. Coordinates quantized to 1e-6. Excludes camera objects, active camera/frame, scene metadata, UI state, file bytes, shader node graphs, light energy and animation between samples.',
        'primary':primary,'rebuilt':rebuilt,'differing_objects':differences,
        'samples':[s['frame'] for s in primary['samples']]}
    (OUT/'reproducibility.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('REPRODUCIBILITY_RESULT',json.dumps(report),flush=True)
    if not report['passed']:raise RuntimeError('Semantic scene fingerprint differs; inspect reproducibility.json')


if __name__=='__main__':main()
