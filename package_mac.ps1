# Tworzy Harmonogramy-Mac.zip na Windows (przed przekazaniem na Maca).
# Uruchom: .\package_mac.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Staging = Join-Path $Root ".package_staging\Harmonogramy"
$Output = Join-Path $Root "Harmonogramy-Mac.zip"

Write-Host "==> Pakowanie aplikacji do Harmonogramy-Mac.zip ..."

if (Test-Path (Join-Path $Root ".package_staging")) {
    Remove-Item -Recurse -Force (Join-Path $Root ".package_staging")
}
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

$FilesToCopy = @(
    "app.py", "config.py", "requirements.txt", "start.command",
    "README_MAC.md", "TEST_MAC.md",
    "personel_wlasciwy.csv", "niedyspozycje.csv"
)
foreach ($f in $FilesToCopy) {
    $src = Join-Path $Root $f
    if (Test-Path $src) {
        Copy-Item $src $Staging
    }
}

Copy-Item -Recurse (Join-Path $Root "modules") $Staging
Copy-Item -Recurse (Join-Path $Root "Harmonogramy.app") $Staging

# Usuń __pycache__ i .pyc
Get-ChildItem -Path (Join-Path $Root ".package_staging") -Recurse -Directory -Filter "__pycache__" |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
Get-ChildItem -Path (Join-Path $Root ".package_staging") -Recurse -Filter "*.pyc" |
    Remove-Item -Force

if (Test-Path $Output) { Remove-Item $Output -Force }
Compress-Archive -Path (Join-Path $Root ".package_staging\Harmonogramy") -DestinationPath $Output -Force

Remove-Item -Recurse -Force (Join-Path $Root ".package_staging")

Write-Host "==> Gotowe: $Output"
Write-Host "    Na Macu uruchom: chmod +x prepare_mac.sh && ./prepare_mac.sh"
