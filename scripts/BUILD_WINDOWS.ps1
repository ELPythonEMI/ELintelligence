param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== ELintelligence Windows / Python build ===" -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher 'py' non trovato. Installa Python 3.12 o 3.13 x64 da python.org."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creo virtual environment..."
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        py -3 -m venv .venv
    }
}

$Python = Resolve-Path ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "ELintelligence.spec") { Remove-Item "ELintelligence.spec" -Force }

$Mode = @("--onedir")
if ($OneFile) { $Mode = @("--onefile") }

$Args = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "ELintelligence",
    "--icon", "assets\icon.ico",
    "--add-data", "assets;assets",
    "--collect-all", "keyring",
    "--hidden-import", "keyring.backends.Windows"
) + $Mode + @("main.py")

& $Python @Args

if ($LASTEXITCODE -ne 0) {
    throw "Build PyInstaller fallita."
}

Write-Host ""
if ($OneFile) {
    Write-Host "EXE creato: $Root\dist\ELintelligence.exe" -ForegroundColor Green
} else {
    Write-Host "Programma creato: $Root\dist\ELintelligence\ELintelligence.exe" -ForegroundColor Green
}
