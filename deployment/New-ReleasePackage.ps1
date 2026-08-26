param(
    [string]$Version = "0.6.0",
    [string]$PythonPath = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$releaseRoot = Join-Path $projectRoot "outputs\releases"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$releaseName = "DestekTakip-$Version-$stamp"
$stageRoot = Join-Path $releaseRoot $releaseName
$zipPath = "$stageRoot.zip"

New-Item -ItemType Directory -Path $stageRoot -ErrorAction Stop | Out-Null

Push-Location $backendRoot
try {
    & $PythonPath -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Backend testleri başarısız." }
    & $PythonPath -m ruff check app tests
    if ($LASTEXITCODE -ne 0) { throw "Backend lint kontrolü başarısız." }
}
finally { Pop-Location }

Push-Location $frontendRoot
try {
    & npm.cmd test
    if ($LASTEXITCODE -ne 0) { throw "Frontend testleri başarısız." }
    & npm.cmd run lint
    if ($LASTEXITCODE -ne 0) { throw "Frontend lint kontrolü başarısız." }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build işlemi başarısız." }
}
finally { Pop-Location }

$stageBackend = New-Item -ItemType Directory -Path (Join-Path $stageRoot "backend")
$stageSite = New-Item -ItemType Directory -Path (Join-Path $stageRoot "site")
$stageDeployment = New-Item -ItemType Directory -Path (Join-Path $stageRoot "deployment")

$sourceApp = Join-Path $backendRoot "app"
$stageApp = New-Item -ItemType Directory -Path (Join-Path $stageBackend.FullName "app")
Get-ChildItem -LiteralPath $sourceApp -File -Recurse | Where-Object {
    $_.Extension -notin @(".pyc", ".pyo") -and $_.FullName -notmatch '[\\/]__pycache__[\\/]'
} | ForEach-Object {
    $relative = [IO.Path]::GetRelativePath($sourceApp, $_.FullName)
    $destination = Join-Path $stageApp.FullName $relative
    $destinationDirectory = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $destination
}
foreach ($name in @("alembic.ini", "pyproject.toml", "README.md", ".env.production.example")) {
    Copy-Item -LiteralPath (Join-Path $backendRoot $name) -Destination $stageBackend.FullName
}
Copy-Item -Path (Join-Path $frontendRoot "dist\*") -Destination $stageSite.FullName -Recurse
Copy-Item -Path (Join-Path $PSScriptRoot "*") -Destination $stageDeployment.FullName -Recurse

$forbidden = Get-ChildItem -LiteralPath $stageRoot -Recurse -Force | Where-Object {
    $_.Name -in @(".env", "node_modules", "__pycache__") -or
    $_.Extension -in @(".db", ".sqlite", ".pyc", ".pyo")
}
if ($forbidden) {
    throw "Yayın paketinde yasaklı yerel dosya bulundu: $($forbidden.FullName -join ', ')"
}

$releaseInfo = @(
    "Uygulama: Destek Takip"
    "Sürüm: $Version"
    "Paket zamanı: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
    "Backend testleri: başarılı"
    "Frontend test/lint/build: başarılı"
) -join [Environment]::NewLine
Set-Content -LiteralPath (Join-Path $stageRoot "RELEASE-INFO.txt") -Value $releaseInfo -Encoding utf8

$checksumPath = Join-Path $stageRoot "SHA256SUMS.txt"
$checksums = Get-ChildItem -LiteralPath $stageRoot -File -Recurse | Where-Object {
    $_.FullName -ne $checksumPath
} | Sort-Object FullName | ForEach-Object {
    $relative = [IO.Path]::GetRelativePath($stageRoot, $_.FullName).Replace("\", "/")
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $relative"
}
Set-Content -LiteralPath $checksumPath -Value $checksums -Encoding ascii

Compress-Archive -LiteralPath $stageRoot -DestinationPath $zipPath -CompressionLevel Optimal
$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()

Write-Host "Yayın paketi oluşturuldu: $zipPath"
Write-Host "SHA256: $zipHash"
