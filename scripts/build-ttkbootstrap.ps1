param()
. "$PSScriptRoot/common.ps1"
Assert-WindowsPython $ProjectPython
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_environment.py'), '--mode', 'build')
& "$PSScriptRoot/test.ps1"
& "$PSScriptRoot/test-ttkbootstrap.ps1"
$RunName = Get-Date -Format 'yyyyMMdd-HHmmss'
$PreviewDist = Join-Path $ProjectRoot "dist/ttkbootstrap-$RunName"
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'freeze.py'), '--noconfirm', '--distpath', $PreviewDist, '--workpath', (Join-Path $ProjectRoot "build/ttkbootstrap-$RunName"), (Join-Path $ProjectRoot 'packaging/TtkbootstrapTesting.spec'))
$PreviewExe = Join-Path $PreviewDist 'ND TranskripThor ttkbootstrap Preview/ND TranskripThor ttkbootstrap Preview.exe'
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_ttkbootstrap_exe.py'), $PreviewExe)
Write-Output $PreviewExe
