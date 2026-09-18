param(
    [string]$LocalRoot = 'D:\AI\化工\工業廢水放流水AI預報',
    [string]$CloudRoot = 'H:\我的雲端硬碟\AI專題\化工\專題一、水處理\工業廢水放流水AI預報'
)
$ErrorActionPreference = 'Stop'
$excludedSegments = @('.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', 'sync-logs')
$copied = 0
$skipped = 0
$localFull = [System.IO.Path]::GetFullPath($LocalRoot).TrimEnd('\')
$cloudFull = [System.IO.Path]::GetFullPath($CloudRoot).TrimEnd('\')
if (-not (Test-Path -LiteralPath $localFull -PathType Container)) { throw "Local root missing: $localFull" }
if (-not (Test-Path -LiteralPath $cloudFull -PathType Container)) { throw "Cloud root missing: $cloudFull" }
foreach ($source in Get-ChildItem -LiteralPath $localFull -File -Recurse) {
    $relative = $source.FullName.Substring($localFull.Length).TrimStart('\')
    $segments = $relative -split '[\\/]'
    if ($segments | Where-Object { $_ -in $excludedSegments }) { $skipped++; continue }
    $target = Join-Path $cloudFull $relative
    $targetDirectory = Split-Path -Parent $target
    if (-not (Test-Path -LiteralPath $targetDirectory)) {
        New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
    }
    $needsCopy = -not (Test-Path -LiteralPath $target)
    if (-not $needsCopy) {
        $existing = Get-Item -LiteralPath $target
        $needsCopy = $source.Length -ne $existing.Length -or $source.LastWriteTimeUtc -gt $existing.LastWriteTimeUtc
    }
    if ($needsCopy) {
        Copy-Item -LiteralPath $source.FullName -Destination $target -Force
        $copied++
    } else {
        $skipped++
    }
}
[pscustomobject]@{
    Timestamp = (Get-Date).ToString('o')
    LocalRoot = $localFull
    CloudRoot = $cloudFull
    Copied = $copied
    Skipped = $skipped
    DeletePropagation = $false
} | ConvertTo-Json -Compress
