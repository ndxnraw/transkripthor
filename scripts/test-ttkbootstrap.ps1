param()
. "$PSScriptRoot/common.ps1"
Assert-WindowsPython $ProjectPython
Invoke-ProjectPython -Arguments @((Join-Path $ProjectRoot 'tests/ttkbootstrap_scenarios.py'))
