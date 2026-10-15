param([string]$UnityEditor = 'C:/Program Files/Unity/Hub/Editor/6000.6.0f1/Editor/Unity.exe')
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
# Unity 6000.6 Linker treats commas in an assembly path as separators. Build a
# plain copy in Temp rather than moving or changing the editable source project.
$stage = Join-Path $env:TEMP ('TowerBridgeUnityE05-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $stage | Out-Null
foreach ($folder in @('Assets','Packages','ProjectSettings')) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $folder) -Destination $stage -Recurse
}
$expected = (Get-FileHash -LiteralPath (Join-Path $projectRoot 'Assets/StreamingAssets/scene.bin') -Algorithm SHA256).Hash
$actual = (Get-FileHash -LiteralPath (Join-Path $stage 'Assets/StreamingAssets/scene.bin') -Algorithm SHA256).Hash
if ($expected -ne $actual) { throw 'Staging copy changed mesh data' }
$log = Join-Path $stage 'editor-build.log'
$process = Start-Process -FilePath $UnityEditor -ArgumentList @('-batchmode','-nographics','-projectPath',('"'+$stage+'"'),'-executeMethod','BridgeBuild.VerifyAndBuild','-quit','-logFile',('"'+$log+'"')) -WindowStyle Hidden -Wait -PassThru
Copy-Item -LiteralPath $log -Destination (Join-Path $projectRoot 'editor-build.log') -Force
if ($process.ExitCode -ne 0) { throw ('Unity build failed; inspect editor-build.log. Staging: '+$stage) }
if (-not (Test-Path -LiteralPath (Join-Path $stage 'Build/verification.json'))) {throw 'Missing successful verification report'}
$output = Join-Path $projectRoot 'Build'
New-Item -ItemType Directory -Path $output -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $stage 'Build') | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $output -Recurse -Force}
Write-Output ('Verified Windows build: '+$output)
Write-Output ('Temporary staging retained for diagnosis: '+$stage)
