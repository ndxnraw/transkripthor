param()
. "$PSScriptRoot/common.ps1"
if ($env:PYTHONPATH -or $env:PYTHONHOME) { throw 'Remove PYTHONPATH and PYTHONHOME before building.' }
Assert-WindowsPython $ProjectPython
Invoke-ProjectPython -Arguments @('-m', 'pip', 'check')
Invoke-ProjectPython -Arguments @((Join-Path $ProjectRoot 'src/check_runtime.py'))
& "$PSScriptRoot/test.ps1"
Invoke-ProjectPython -Arguments @('-m', 'PyInstaller', '--noconfirm', '--clean', '--distpath', (Join-Path $ProjectRoot 'dist'), '--workpath', (Join-Path $ProjectRoot 'build'), (Join-Path $ProjectRoot 'packaging/TranskripTHOR.spec'))
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_frozen.py'), (Join-Path $ProjectRoot 'dist/ND TranskripThor/ND TranskripThor.exe'))
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_exe.py'), (Join-Path $ProjectRoot 'dist/ND TranskripThor/ND TranskripThor.exe'))
