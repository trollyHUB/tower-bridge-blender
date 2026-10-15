[CmdletBinding()]
param(
    [ValidateSet('Build', 'Validate', 'Stills', 'Animation', 'Encode', 'Finalize', 'Benchmark', 'VideoCheck', 'Preview')]
    [string]$Action = 'Validate',
    [string]$BlenderPath,
    [ValidateRange(1, 1000000)]
    [int]$StartFrame = 1,
    [ValidateRange(0, 1000000)]
    [int]$EndFrame = 0
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

if (-not $BlenderPath) {
    $blenderCommand = Get-Command blender -ErrorAction SilentlyContinue
    if ($blenderCommand) {
        $BlenderPath = $blenderCommand.Source
    } else {
        $BlenderPath = Join-Path $env:ProgramFiles 'Blender Foundation\Blender 5.2\blender.exe'
    }
}
if (-not (Test-Path -LiteralPath $BlenderPath -PathType Leaf)) {
    throw 'Blender was not found. Supply -BlenderPath with the path to blender.exe.'
}
$sceneConfig = Get-Content -LiteralPath (Join-Path $projectRoot 'config/scene.json') -Raw | ConvertFrom-Json
$frameCount = [int]($sceneConfig.fps * $sceneConfig.duration_seconds)
if ($EndFrame -eq 0) { $EndFrame = $frameCount }
if ($StartFrame -gt $frameCount -or $EndFrame -gt $frameCount) { throw 'Requested frames exceed the configured duration.' }
if ($StartFrame -gt $EndFrame) {
    throw 'StartFrame must not exceed EndFrame.'
}

$blenderArgs = @('--background', '--python-exit-code', '1', '--python')
if ($Action -eq 'Build') {
    $blenderArgs += Join-Path $projectRoot 'build_tower_bridge.py'
} else {
    $blenderArgs += Join-Path $projectRoot 'render_tower_bridge.py'
    $mode = if ($Action -eq 'VideoCheck') { 'video_check' } else { $Action.ToLowerInvariant() }
    $blenderArgs += @('--', $mode)
    if ($Action -in @('Animation', 'Preview')) {
        $blenderArgs += @([string]$StartFrame, [string]$EndFrame)
    }
}

Push-Location -LiteralPath $projectRoot
try {
    & $BlenderPath @blenderArgs
    $blenderExitCode = $LASTEXITCODE
    if ($blenderExitCode -ne 0) {
        throw "Blender failed with exit code $blenderExitCode."
    }
} finally {
    Pop-Location
}


