param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AppArguments)
. "$PSScriptRoot/common.ps1"
if ($env:PYTHONPATH -or $env:PYTHONHOME) { throw 'Remove PYTHONPATH and PYTHONHOME before running.' }
Invoke-ProjectPython -Arguments (@((Join-Path $ProjectRoot 'src/prepis.py')) + $AppArguments)
