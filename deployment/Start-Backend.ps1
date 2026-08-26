param(
    [int]$Workers = 2
)

$ErrorActionPreference = "Stop"
$backendRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\backend"))
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"
$envPath = Join-Path $backendRoot ".env"

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Backend sanal ortamı bulunamadı: $pythonPath"
}
if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    throw "Üretim .env dosyası bulunamadı: $envPath"
}

Push-Location $backendRoot
try {
    & $pythonPath -m app.cli.preflight
    if ($LASTEXITCODE -ne 0) { throw "Üretim ön kontrolü başarısız." }

    & $pythonPath -m uvicorn app.main:app `
        --host 127.0.0.1 `
        --port 8000 `
        --workers $Workers `
        --proxy-headers `
        --forwarded-allow-ips 127.0.0.1
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
