param(
    [ValidateSet('3.14', '3.15')][string]$PythonVersion = '3.15',
    [ValidateSet('CPU', 'CUDA')][string]$TorchBuild = 'CUDA',
    [string]$InstallationPath = '',
    [string]$OriginalTorchWheel = '',
    [switch]$WithWandb
)

$ErrorActionPreference = 'Stop'
$taskTag = 'cp' + $PythonVersion.Replace('.', '')
$taskRuntime = Join-Path $PSScriptRoot ('runtime\python' + $PythonVersion.Replace('.', '') + '\python.exe')
$taskManifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-info.json') -Raw | ConvertFrom-Json
if ($taskManifest.windows_support.$PythonVersion -notcontains $TorchBuild) {
    throw 'This runtime/backend combination is not supported by this bundle. No files were changed.'
}
if ($taskManifest.pytorch.binding_source -ne 'official' -or $taskManifest.pytorch.version -ne '2.15.0') {
    throw 'This installer requires the official PyTorch 2.15 build manifest. No files were changed.'
}
$taskTorchArtifact = $taskManifest.pytorch.wheels.($PythonVersion + '-' + $TorchBuild)
$taskVisionArtifact = $taskManifest.pytorch.torchvision.$TorchBuild
if (-not $taskTorchArtifact -or -not $taskVisionArtifact) { throw 'Missing official wheel profile. No files were changed.' }
if ($OriginalTorchWheel -and (Get-FileHash -LiteralPath $OriginalTorchWheel -Algorithm SHA256).Hash -ne $taskTorchArtifact.sha256) {
    throw 'Cached official Torch wheel checksum differs from the selected profile. No files were changed.'
}
foreach ($taskEntry in $taskManifest.files) {
    $taskFile = Join-Path $PSScriptRoot $taskEntry.path
    if (-not (Test-Path -LiteralPath $taskFile) -or (Get-FileHash -LiteralPath $taskFile -Algorithm SHA256).Hash -ne $taskEntry.sha256) {
        throw ('Package integrity check failed: ' + $taskEntry.path)
    }
}
if (-not $InstallationPath) { $InstallationPath = Join-Path $PSScriptRoot ('pylaia-env-' + $PythonVersion) }
if (Test-Path -LiteralPath $InstallationPath) { throw 'The installation folder already exists. Choose a new -InstallationPath to preserve existing files.' }

Write-Host ('Creating an isolated PyLaia environment with Python ' + $PythonVersion)
& $taskRuntime -m venv $InstallationPath
if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
$taskPython = Join-Path $InstallationPath 'Scripts\python.exe'
& $taskPython -m pip install --upgrade 'pip==26.2.2'
if ($LASTEXITCODE -ne 0) { throw 'Isolated installer update failed.' }
Write-Host ('Installing SHA256-pinned official PyTorch packages (' + $TorchBuild + ')')
if ($OriginalTorchWheel) {
    & $taskPython -m pip install --no-deps $OriginalTorchWheel
} else {
    & $taskPython -m pip install --no-deps ($taskTorchArtifact.url + '#sha256=' + $taskTorchArtifact.sha256)
}
if ($LASTEXITCODE -ne 0) { throw 'PyTorch installation failed.' }
& $taskPython -m pip install --no-deps ($taskVisionArtifact.url + '#sha256=' + $taskVisionArtifact.sha256)
if ($LASTEXITCODE -ne 0) { throw 'TorchVision installation failed.' }
Write-Host 'Installing local Flashlight/KenLM and PyLaia'
$taskCompatibility = Join-Path $PSScriptRoot 'compatibility'
$taskSympy = Join-Path $taskCompatibility 'sympy-1.14.0+pylaia1-py3-none-any.whl'
$taskMpmath = Join-Path $taskCompatibility 'mpmath-1.4.1-py3-none-any.whl'
$taskWheelFolder = Join-Path $PSScriptRoot ('wheels\' + $taskTag)
$taskKenlm = Join-Path $taskWheelFolder ('kenlm-0.3.0+pylaia1-' + $taskTag + '-' + $taskTag + '-win_amd64.whl')
$taskFlashlight = Join-Path $taskWheelFolder ('flashlight_text-0.0.7+pylaia1-' + $taskTag + '-' + $taskTag + '-win_amd64.whl')
$taskPylaia = Join-Path $PSScriptRoot ('wheels\' + $taskManifest.pylaia_wheel)
$taskInstallTargets = @($taskSympy, $taskMpmath, $taskKenlm, $taskFlashlight, ($taskPylaia + '[language-model]'))
if ($WithWandb) {
    $taskInstallTargets += @((Join-Path $taskCompatibility 'wandb-0.31.0+pylaia1-py3-none-win_amd64.whl'), (Join-Path $taskCompatibility 'cwevals-0.0.1b2-py3-none-any.whl'))
}
if ($PythonVersion -eq '3.15') {
    $taskBidi = Join-Path $taskWheelFolder 'python_bidi-0.6.12-cp315-cp315-win_amd64.whl'
    $taskYaml = Join-Path $taskWheelFolder 'pyyaml-6.0.3-cp315-cp315-win_amd64.whl'
    $taskInstallTargets += @($taskBidi, $taskYaml)
}
& $taskPython -m pip install @taskInstallTargets
if ($LASTEXITCODE -ne 0) { throw 'PyLaia installation failed.' }
& $taskPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
$taskSmoke = Join-Path $PSScriptRoot 'verify-installation.py'
$taskSmokeArgs = @('-I', $taskSmoke)
if ($TorchBuild -eq 'CUDA') { $taskSmokeArgs += '--require-cuda' }
if ($WithWandb) { $taskSmokeArgs += '--check-wandb' }
& $taskPython @taskSmokeArgs
if ($LASTEXITCODE -ne 0) { throw 'Installation test failed.' }
Write-Host ('Installation verified. Commands are in: ' + (Join-Path $InstallationPath 'Scripts'))
