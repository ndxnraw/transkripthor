param()
. "$PSScriptRoot/common.ps1"
if ($env:PYTHONPATH -or $env:PYTHONHOME) { throw 'Remove PYTHONPATH and PYTHONHOME before testing.' }
Assert-WindowsPython $ProjectPython
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'run_tests.py'))
