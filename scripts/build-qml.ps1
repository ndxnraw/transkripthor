param()
# Stable build is a mandatory full regression gate, including its new Windows EXE.
& "$PSScriptRoot/build.ps1"
& "$PSScriptRoot/test-qml.ps1"
. "$PSScriptRoot/common.ps1"
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'freeze.py'),'--noconfirm','--clean','--distpath',(Join-Path $ProjectRoot 'dist'),'--workpath',(Join-Path $ProjectRoot 'build/qml'),(Join-Path $ProjectRoot 'packaging/QmlTesting.spec'))
$QmlExe = Join-Path $ProjectRoot 'dist/ND TranskripThor QML Testing/ND TranskripThor QML Testing.exe'
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_frozen.py'),$QmlExe,'--qml')
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_qml_exe.py'),$QmlExe)
