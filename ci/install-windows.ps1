param(
    [ValidateSet('3.13', '3.14')][string]$PythonVersion = '3.14',
    [ValidateSet('CPU', 'CUDA')][string]$TorchBuild = 'CUDA',
    [string]$InstallationPath = ''
)

$ErrorActionPreference = 'Stop'
$taskTag = 'cp' + $PythonVersion.Replace('.', '')
$taskRuntime = Join-Path $PSScriptRoot ('runtime\python' + $PythonVersion.Replace('.', '') + '\python.exe')
$taskManifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-info.json') -Raw | ConvertFrom-Json
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
$taskTorchIndex = 'https://download.pytorch.org/whl/cpu'
if ($TorchBuild -eq 'CUDA') { $taskTorchIndex = 'https://download.pytorch.org/whl/cu130' }
Write-Host ('Installing official PyTorch packages (' + $TorchBuild + ')')
& $taskPython -m pip install --no-deps 'torch==2.14.1' 'torchvision==0.29.1' --index-url $taskTorchIndex
if ($LASTEXITCODE -ne 0) { throw 'PyTorch installation failed.' }
Write-Host 'Installing local Flashlight/KenLM and PyLaia'
$taskWheelFolder = Join-Path $PSScriptRoot ('wheels\' + $taskTag)
$taskKenlm = Join-Path $taskWheelFolder ('kenlm-0.3.0+pylaia1-' + $taskTag + '-' + $taskTag + '-win_amd64.whl')
$taskFlashlight = Join-Path $taskWheelFolder ('flashlight_text-0.0.7+pylaia1-' + $taskTag + '-' + $taskTag + '-win_amd64.whl')
$taskPylaia = Join-Path $PSScriptRoot ('wheels\' + $taskManifest.pylaia_wheel)
& $taskPython -m pip install --no-deps $taskKenlm $taskFlashlight
if ($LASTEXITCODE -ne 0) { throw 'Local native package installation failed.' }
& $taskPython -m pip install ($taskPylaia + '[language-model]')
if ($LASTEXITCODE -ne 0) { throw 'PyLaia installation failed.' }
& $taskPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
$taskSmoke = Join-Path $PSScriptRoot 'verify-installation.py'
$taskSmokeArgs = @('-I', $taskSmoke)
if ($TorchBuild -eq 'CUDA') { $taskSmokeArgs += '--require-cuda' }
& $taskPython @taskSmokeArgs
if ($LASTEXITCODE -ne 0) { throw 'Installation test failed.' }
Write-Host ('Installation verified. Commands are in: ' + (Join-Path $InstallationPath 'Scripts'))
