param([Parameter(Mandatory = $true)][string]$Output)
$ErrorActionPreference = 'Stop'
$Output = [IO.Path]::GetFullPath($Output)
if (Test-Path -LiteralPath $Output) { throw 'Refusing to overwrite audio.' }
New-Item -ItemType Directory -Path (Split-Path -Parent $Output) -Force | Out-Null
$Voice = New-Object -ComObject SAPI.SpVoice
$Stream = New-Object -ComObject SAPI.SpFileStream
try {
    $Stream.Open($Output, 3, $false)
    $Voice.AudioOutputStream = $Stream
    [void]$Voice.Speak('Hello. This is a test of local speech transcription. The recording is synthetic. All data stays on this computer. We are testing projects, subtitles, and process startup.')
}
finally {
    $Stream.Close()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($Stream)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($Voice)
}
Write-Output "Synthetic Windows speech saved: $Output"
