$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ProjectPython = Join-Path $ProjectRoot '.venv/Scripts/python.exe'

function Invoke-ProjectPython {
    param([string[]]$Arguments)
    if (!(Test-Path -LiteralPath $ProjectPython)) { throw 'Run scripts/setup.ps1 first.' }
    & $ProjectPython @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python failed with exit code $LASTEXITCODE" }
}

function Assert-WindowsPython {
    param([string]$Executable, [string[]]$Prefix = @())
    & $Executable @Prefix -c "import sys, struct, tkinter; assert sys.platform == 'win32' and sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8, 'Windows x64 Python 3.12 required'; print(sys.version); print('Tk', tkinter.Tcl().eval('info patchlevel'))"
    if ($LASTEXITCODE -ne 0) { throw 'Windows x64 Python 3.12 with Tk is required.' }
}
