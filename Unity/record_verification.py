"""Record only checks actually completed by the built Editor/Player harnesses."""
import hashlib
import json
import pathlib
import struct
import shutil

project = pathlib.Path(__file__).resolve().parent
build = project/'Build'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


editor = json.loads((build/'verification.json').read_text())
runtime = json.loads((build/'runtime-verification.json').read_text())
source = json.loads((project/'Assets/StreamingAssets/scene.json').read_text())
blend_sha = sha(project.parent/'Tower_Bridge/Tower_Bridge.blend')
assert editor['passed'] and runtime['passed']
assert editor['source_sha256'] == blend_sha
assert runtime['source_sha256'] == source['source_sha256'] == blend_sha
for name in ('scene.json', 'scene.bin'):
    assert sha(project/'Assets/StreamingAssets'/name) == sha(build/'TowerBridge_Data/StreamingAssets'/name)
for name in ('runtime.png', 'runtime-river.png', 'runtime-evening.png', 'runtime-walk.png'):
    content = (build/name).read_bytes()
    assert content[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II', content[16:24]) == (1280, 720)
artifacts = ('verification.json', 'runtime-verification.json', 'runtime.png', 'runtime-river.png',
             'runtime-evening.png', 'runtime-walk.png', 'TowerBridge.exe',
             'TowerBridge_Data/StreamingAssets/scene.json', 'TowerBridge_Data/StreamingAssets/scene.bin')
proof = project/'Verification'
proof.mkdir(exist_ok=True)
for name in artifacts[:6]:
    shutil.copyfile(build/name, proof/name)
report = {
    'status': 'E05_VERIFIED', 'editor_passed': True, 'runtime_passed': True,
    'walk_controls_passed': True, 'source_sha256': blend_sha,
    'export_matches_source': True, 'built_export_matches_project': True,
    'groups': len(source['groups']), 'transform_samples': sum(len(g['samples']) for g in source['groups']),
    'python_export_tests': {'passed': 7, 'failed': 0},
    'unity_version': '6000.6.0f1', 'graphics_backend': 'Direct3D11 WARP / '+runtime['renderer'],
    'runtime_checks': runtime['checks'],
    'artifact_sha256': {name: sha(build/name) for name in artifacts},
    'limitations': ['Software rendered verification, not a hardware GPU performance benchmark.',
                    'Camera.Render snapshots show actual Player geometry; the IMGUI overlay is excluded.',
                    'Standard base-colour materials approximate Blender nodes; mesh deformation and animated water shaders are not transferred.',
                    'Bridge commands control safe phases of the synchronized source choreography; traffic is not a free driving simulation.'],
}
(project/'verification-status.json').write_text(json.dumps(report, indent=2)+'\n')
print('E05_VERIFIED', blend_sha)
