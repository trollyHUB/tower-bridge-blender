"""Compile sources against installed Unity assemblies; does not run/activate Unity."""
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent
editor = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else r'C:/Program Files/Unity/Hub/Editor/6000.6.0f1/Editor')
data = editor/'Data'
refs = list((data/'Managed/UnityEngine').glob('*.dll'))
refs += list((data/'DotNetSdk/packs/NETStandard.Library.Ref/2.1.0/ref/netstandard2.1').glob('*.dll'))
args = ['-nostdlib+', '-target:library', f'-out:{root}/compile-verification.dll']
args += [f'-r:{p}' for p in refs]
args += [str(root/'Assets/Scripts/BridgeScene.cs'), str(root/'Assets/Editor/BridgeBuild.cs')]
(root/'compile.rsp').write_text('\n'.join('"'+arg+'"' for arg in args), encoding='utf-8-sig')
result = subprocess.run([str(data/'DotNetSdk/dotnet.exe'), str(data/'DotNetSdk/sdk/8.0.318/Roslyn/bincore/csc.dll'), '@'+str(root/'compile.rsp')], capture_output=True)
(root/'compile-verification.log').write_bytes(result.stdout + result.stderr)
print(result.stdout.decode(errors='replace'))
print(result.stderr.decode(errors='replace'))
raise SystemExit(result.returncode)
