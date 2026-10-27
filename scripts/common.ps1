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
    $ExpectedPython = (Get-Content -LiteralPath (Join-Path $ProjectRoot '.python-version') -Raw).Trim()
    & $Executable @Prefix -c "import sys, struct, tkinter, platform; assert sys.platform == 'win32' and platform.python_implementation() == 'CPython' and platform.python_version() == sys.argv[1] and struct.calcsize('P') == 8, 'Pinned Windows x64 CPython required'; print(sys.version); print('Tk', tkinter.Tcl().eval('info patchlevel'))" $ExpectedPython
    if ($LASTEXITCODE -ne 0) { throw "Windows x64 CPython $ExpectedPython with Tk is required; existing environment was preserved." }
}
