param(
    [Parameter(Mandatory = $true)]
    [uri]$BaseUrl
)

$ErrorActionPreference = "Stop"
$root = $BaseUrl.AbsoluteUri.TrimEnd("/")
$checks = @(
    @{ Name = "Frontend"; Url = "$root/"; ContentType = "text/html" },
    @{ Name = "API canlılık"; Url = "$root/api/health/live"; ContentType = "application/json" },
    @{ Name = "MSSQL hazırlık"; Url = "$root/api/health/ready"; ContentType = "application/json" }
)

foreach ($check in $checks) {
    $response = Invoke-WebRequest -Uri $check.Url -Method Get -TimeoutSec 15 -UseBasicParsing
    if ($response.StatusCode -ne 200) {
        throw "$($check.Name) kontrolü HTTP $($response.StatusCode) döndürdü."
    }
    if ($response.Headers["Content-Type"] -notlike "$($check.ContentType)*") {
        throw "$($check.Name) beklenmeyen içerik türü döndürdü."
    }
    Write-Host "[OK] $($check.Name) — $($check.Url)"
}

Write-Host "Anonim yayın kontrolleri tamamlandı. Rol bazlı akışlar için kabul listesini uygulayın."
