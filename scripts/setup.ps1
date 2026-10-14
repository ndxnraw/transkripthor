param(
    [ValidateSet('runtime', 'development', 'build')][string]$Mode = 'development',
    [string]$Python,
    [switch]$Speakers
)
. "$PSScriptRoot/common.ps1"
if ($env:PYTHONPATH -or $env:PYTHONHOME) {
    throw 'Remove PYTHONPATH and PYTHONHOME before setup; external Python packages are not supported.'
}
if (!(Test-Path -LiteralPath $ProjectPython)) {
    if ($Python) { $Executable = $Python; $Prefix = @() }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { $Executable = 'py'; $Prefix = @('-3.12') }
    else { $Executable = 'python'; $Prefix = @() }
    Assert-WindowsPython $Executable $Prefix
    & $Executable @Prefix -m venv (Join-Path $ProjectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed; the existing environment was not deleted.' }
}
Assert-WindowsPython $ProjectPython
$Lock = if ($Mode -eq 'build') { 'build.lock' } else { 'runtime.lock' }
Invoke-ProjectPython -Arguments @('-m', 'pip', 'install', '--require-hashes', '--only-binary=:all:', '-r', (Join-Path $ProjectRoot "requirements/$Lock"))
if ($Speakers -or $Mode -eq 'build') {
    Invoke-ProjectPython -Arguments @('-m', 'pip', 'install', '--require-hashes', '--only-binary=:all:', '-r', (Join-Path $ProjectRoot 'requirements/speakers.lock'))
}
Invoke-ProjectPython -Arguments @('-m', 'pip', 'check')
