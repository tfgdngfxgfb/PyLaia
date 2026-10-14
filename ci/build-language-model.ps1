param(
    [string]$Python = 'python',
    [switch]$Install
)

$ErrorActionPreference = 'Stop'
$taskVsWhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path -LiteralPath $taskVsWhere)) {
    throw 'Install Visual Studio 2022 Build Tools with Desktop development with C++ first.'
}
$taskCompiler = & $taskVsWhere -latest -version '[17.0,18.0)' -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $taskCompiler) { throw 'Visual Studio 2022 MSVC x64 Build Tools are required.' }
$taskVcVars = Join-Path $taskCompiler 'VC\Auxiliary\Build\vcvars64.bat'
$taskEnvironment = & $env:ComSpec /d /c ('call "' + $taskVcVars + '" >nul && set')
if ($LASTEXITCODE -ne 0) { throw 'Compiler setup failed.' }
foreach ($taskLine in $taskEnvironment) {
    if ($taskLine -match '^(PATH|INCLUDE|LIB|LIBPATH|WindowsSDKVersion|WindowsSdkDir|VCToolsInstallDir)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
$taskBuilder = Join-Path $PSScriptRoot 'build_language_model.py'
if ($Install) { & $Python $taskBuilder --install } else { & $Python $taskBuilder }
if ($LASTEXITCODE -ne 0) { throw 'Language-model build failed; see the error above.' }
