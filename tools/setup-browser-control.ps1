# Run on the Windows PC that runs Codex, not in the Linux cloud shell.
$ErrorActionPreference = 'Stop'
if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npx.cmd -ErrorAction SilentlyContinue)) {
    throw 'Pasang Node.js 24 LTS (termasuk npm/npx), kemudian buka PowerShell semula.'
}
$nodeMajor = [int]((& node --version).TrimStart('v').Split('.')[0])
if ($nodeMajor -lt 24) { throw 'Node.js 24+ diperlukan untuk setup ini.' }
$chromeCandidates = @()
foreach ($installRoot in @($env:PROGRAMFILES, ${env:PROGRAMFILES(X86)}, $env:LOCALAPPDATA)) {
    if ($installRoot) { $chromeCandidates += Join-Path $installRoot 'Google\Chrome\Application\chrome.exe' }
}
$chromePath = $chromeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $chromePath) { throw 'Google Chrome tidak ditemui. Pasang Chrome Stable dahulu.' }
# Validate the pinned official server before editing Codex config.
& npx.cmd -y chrome-devtools-mcp@1.13.0 --version
if ($LASTEXITCODE -ne 0) { throw 'Pemasangan server MCP gagal; config tidak diubah.' }
$codexConfigRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
New-Item -ItemType Directory -Force -Path $codexConfigRoot | Out-Null
$configFile = Join-Path $codexConfigRoot 'config.toml'
$contents = if (Test-Path -LiteralPath $configFile) { [IO.File]::ReadAllText($configFile) } else { '' }
if ($contents -match '(?im)^[^#\r\n]*chrome-devtools') {
    Write-Host 'Rujukan chrome-devtools sudah ada dalam config; config sedia ada dikekalkan.'
    Write-Host 'Semak entri sedia ada jika sambungan masih gagal. Tiada token/cookie perlu disalin.'
    exit 0
}
# JSON quoted strings are compatible with the TOML basic strings used here.
$chromeArg = ConvertTo-Json -Compress -InputObject "--executablePath=$chromePath"
$section = @"

[mcp_servers.chrome-devtools]
command = "cmd"
args = ["/d", "/c", "npx", "-y", "chrome-devtools-mcp@1.13.0", "--headless=false", "--no-usage-statistics", "--no-performance-crux", $chromeArg]
startup_timeout_sec = 60
"@
if (Test-Path -LiteralPath $configFile) {
    $backup = "$configFile.before-browser-control.$([DateTime]::UtcNow.ToString('yyyyMMddHHmmssfff'))"
    Copy-Item -LiteralPath $configFile -Destination $backup -ErrorAction Stop
}
[IO.File]::AppendAllText($configFile, "`n" + $section + "`n", [Text.UTF8Encoding]::new($false))
Write-Host "Konfigurasi disimpan: $configFile"
Write-Host 'Tutup dan buka semula Codex. Mulakan task LOCAL pada PC ini (bukan cloud setup).'
Write-Host 'Minta agent menggunakan chrome-devtools.list_pages/new_page untuk buka Google AI Studio.'
Write-Host 'Alat ini membuka Chrome yang dikawal MCP. Ia tidak mengawal tab browser terbina dalam Codex secara automatik.'
Write-Host 'Login Google sendiri dalam Chrome tersebut apabila diminta.'
