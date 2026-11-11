param([string]$Python)
& "$PSScriptRoot/setup.ps1" -Mode build -Python $Python
. "$PSScriptRoot/common.ps1"
Invoke-ProjectPython -Arguments @('-m', 'pip', 'install', '--require-hashes', '--only-binary=:all:', '-r', (Join-Path $ProjectRoot 'requirements/ttkbootstrap.lock'))
Invoke-ProjectPython -Arguments @('-m', 'pip', 'check')
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_environment.py'), '--mode', 'build')
