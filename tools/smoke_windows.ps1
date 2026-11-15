$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $base 'resources\runtime\python\python.exe'
$engine = Join-Path $base 'resources\engine\tools\video.py'
$env:PATH = (Join-Path $base 'resources\runtime\bin') + ';' + $env:PATH
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$manifest = Get-Content (Join-Path $base 'SHA256SUMS.json') -Raw | ConvertFrom-Json
foreach ($entry in $manifest.PSObject.Properties) {
    $actual = (Get-FileHash (Join-Path $base $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $entry.Value) { throw "SHA256 mismatch: $($entry.Name)" }
}
& $python -c 'import sys, numpy, scipy, PIL, pypdf; print(sys.version); print("PYTHON_PACKAGES_OK")'
if ($LASTEXITCODE -ne 0) { throw 'Bundled Python failed' }
& ffmpeg -version
if ($LASTEXITCODE -ne 0) { throw 'Bundled FFmpeg failed' }
& ffprobe -version
if ($LASTEXITCODE -ne 0) { throw 'Bundled FFprobe failed' }
$temp = Join-Path $base ('Data\smoke-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
$env:OWNVIDEO_WORKSPACE = $temp
try {
    $source = Join-Path $temp 'bahan.txt'
    Set-Content -Path $source -Encoding utf8 -Value "# Ujian`nIni ujian portable Windows."
    $result = & $python $engine new 'Ujian Windows' --source $source
    if ($LASTEXITCODE -ne 0) { throw 'Project creation failed' }
    $record = ($result | Where-Object { $_ -like 'PORTABLE_RESULT=*' } | Select-Object -Last 1).Substring(16) | ConvertFrom-Json
    $project = $record.project
    $wav = Join-Path $project 'audio\s01.wav'
    & ffmpeg -hide_banner -loglevel error -f lavfi -i 'sine=frequency=220:duration=3:sample_rate=24000' -ac 1 $wav
    if ($LASTEXITCODE -ne 0) { throw 'Audio fixture failed' }
    '[{"start":0,"end":3,"text":"Ini ujian portable Windows."}]' | Set-Content -Encoding utf8 (Join-Path $project 'audio\s01.cues.json')
    & $python $engine render $project --workers 1
    if ($LASTEXITCODE -ne 0) { throw 'Windows render failed' }
    $info = Get-Content (Join-Path $project 'project.json') -Raw | ConvertFrom-Json
    if ($info.status -ne 'RENDERED') { throw 'No rendered output' }
    if (-not (Test-Path (Join-Path $project $info.final_video))) { throw 'MP4 missing' }
    Write-Host 'WINDOWS_PORTABLE_SMOKE_PASSED (synthetic tone; no Google generation)'
} finally {
    Remove-Item -Recurse -Force $temp
}
