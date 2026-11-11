param([string]$OutputDirectory)
. "$PSScriptRoot/common.ps1"
Assert-WindowsPython $ProjectPython
if ($env:PYTHONPATH -or $env:PYTHONHOME) { throw 'Remove PYTHONPATH and PYTHONHOME before building.' }
$DistributionRoot = if ($OutputDirectory) { $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory) } else { Join-Path $ProjectRoot ('dist/qt-' + (Get-Date -Format 'yyyyMMdd-HHmmss')) }
$AppDirectory = Join-Path $DistributionRoot 'ND TranskripThor'
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'build_receipt.py'), 'begin', $AppDirectory)
Invoke-ProjectPython -Arguments @('-m', 'pip', 'check')
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_environment.py'), '--mode', 'build')
& "$PSScriptRoot/test.ps1"
& "$PSScriptRoot/test-qt.ps1"
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'freeze.py'), '--noconfirm', '--clean', '--distpath', $DistributionRoot, '--workpath', (Join-Path $ProjectRoot 'build/qt-production'), (Join-Path $ProjectRoot 'packaging/Qml.spec'))
Set-Content -LiteralPath (Join-Path $AppDirectory '_internal/distribution-variant.txt') -Value 'extended' -Encoding ascii
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_frozen.py'), (Join-Path $AppDirectory 'ND TranskripThor.exe'), '--qt')
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_qt_exe.py'), (Join-Path $AppDirectory 'ND TranskripThor.exe'))
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'build_receipt.py'), 'create', $AppDirectory, '--frontend', 'qt')
