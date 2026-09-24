$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $env:LOCALAPPDATA "ELintelligence"
$Target = Join-Path $Root "data"

Write-Host "=== ELintelligence: migrazione AppData -> USB ===" -ForegroundColor Cyan
if (-not (Test-Path $Source)) {
    Write-Host "Nessuna installazione trovata in $Source" -ForegroundColor Yellow
    exit 0
}
New-Item -ItemType Directory -Force -Path $Target | Out-Null
Write-Host "Origine: $Source"
Write-Host "Destinazione: $Target"
robocopy $Source $Target /E /COPY:DAT /R:2 /W:1 /NFL /NDL /NP
$code = $LASTEXITCODE
if ($code -ge 8) { throw "Robocopy fallita con codice $code" }
Write-Host "Migrazione completata. Ora ELintelligence usera' i dati sulla penna USB." -ForegroundColor Green
