param()
. "$PSScriptRoot/common.ps1"
Assert-WindowsPython $ProjectPython
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_environment.py'), '--mode', 'development')
Invoke-ProjectPython -Arguments @((Join-Path $ProjectRoot 'tests/qt_app_scenarios.py'))
