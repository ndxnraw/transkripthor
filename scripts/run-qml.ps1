param([string]$Profile)
. "$PSScriptRoot/common.ps1"
Assert-WindowsPython $ProjectPython
$Arguments = @((Join-Path $ProjectRoot 'src/prototype_qml/main.py'))
if ($Profile) { $Arguments += @('--profile', $Profile) }
Invoke-ProjectPython -Arguments $Arguments
