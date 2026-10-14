param(
    [string]$Python = 'python',
    [ValidateSet('CPU', 'CUDA')][string]$TorchBuild = 'CPU',
    [string]$WorkDirectory = '',
    [string]$OutputDirectory = '',
    [string]$OriginalWheel = '',
    [string]$CudaRoot = '',
    [int]$Jobs = 4
)
$ErrorActionPreference = 'Stop'
$taskVsWhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$taskCompiler = & $taskVsWhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $taskCompiler) { throw 'MSVC x64 Build Tools are required.' }
$taskVcVars = Join-Path $taskCompiler 'VC\Auxiliary\Build\vcvars64.bat'
$taskEnvironment = & $env:ComSpec /d /c ('call "' + $taskVcVars + '" >nul && set')
if ($LASTEXITCODE -ne 0) { throw 'Compiler setup failed.' }
foreach ($taskLine in $taskEnvironment) {
    if ($taskLine -match '^(PATH|INCLUDE|LIB|LIBPATH|WindowsSDKVersion|WindowsSdkDir|VCToolsInstallDir)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
$taskArguments = @((Join-Path $PSScriptRoot 'build_torch315.py'), '--build', $TorchBuild, '--jobs', $Jobs)
foreach ($taskPair in @(
    @('--work-dir', $WorkDirectory), @('--output-dir', $OutputDirectory),
    @('--original-wheel', $OriginalWheel), @('--cuda-root', $CudaRoot)
)) {
    if ($taskPair[1]) { $taskArguments += $taskPair }
}
& $Python @taskArguments
if ($LASTEXITCODE -ne 0) { throw 'PyTorch Python 3.15 binding rebuild failed.' }
