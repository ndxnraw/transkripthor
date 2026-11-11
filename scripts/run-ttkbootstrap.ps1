param()
. "$PSScriptRoot/common.ps1"
Assert-WindowsPython $ProjectPython
Invoke-ProjectPython -Arguments @((Join-Path $ProjectRoot 'src/prototype_ttkbootstrap/main.py'))
