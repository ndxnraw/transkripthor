param([ValidateSet('extended', 'basic')][string]$Variant = 'extended')
. "$PSScriptRoot/common.ps1"
$DistributionRoot = if ($Variant -eq 'basic') { Join-Path $ProjectRoot 'dist/basic' } else { Join-Path $ProjectRoot 'dist' }
$AppDirectory = Join-Path $DistributionRoot 'ND TranskripThor'
$Spec = if ($Variant -eq 'basic') { 'Basic.spec' } else { 'TranskripTHOR.spec' }
if ($env:PYTHONPATH -or $env:PYTHONHOME) { throw 'Remove PYTHONPATH and PYTHONHOME before building.' }
Assert-WindowsPython $ProjectPython
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'build_receipt.py'), 'begin', $AppDirectory)
Invoke-ProjectPython -Arguments @('-m', 'pip', 'check')
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_environment.py'), '--mode', 'build')
Invoke-ProjectPython -Arguments @((Join-Path $ProjectRoot 'src/check_runtime.py'))
& "$PSScriptRoot/test.ps1"
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'freeze.py'), '--noconfirm', '--clean', '--distpath', $DistributionRoot, '--workpath', (Join-Path $ProjectRoot "build/$Variant"), (Join-Path $ProjectRoot "packaging/$Spec"))
Set-Content -LiteralPath (Join-Path $AppDirectory '_internal/distribution-variant.txt') -Value $Variant -Encoding ascii
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_frozen.py'), (Join-Path $AppDirectory 'ND TranskripThor.exe'))
Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'verify_exe.py'), (Join-Path $AppDirectory 'ND TranskripThor.exe'))

Invoke-ProjectPython -Arguments @((Join-Path $PSScriptRoot 'build_receipt.py'), 'create', $AppDirectory)
