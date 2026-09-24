$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher 'py' non trovato. Installa Python 3.12 x64 da python.org."
}
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { py -3 -m venv .venv }
}
$Python = Resolve-Path ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "ELintelligence.spec") { Remove-Item "ELintelligence.spec" -Force }

& $Python -m PyInstaller --noconfirm --clean --windowed --onefile `
    --name ELintelligence `
    --icon "assets\icon.ico" `
    --add-data "assets;assets" `
    --collect-all keyring `
    --hidden-import keyring.backends.Windows `
    main.py
if ($LASTEXITCODE -ne 0) { throw "Build PyInstaller fallita." }

$Usb = Join-Path $Root "USB_READY"
if (Test-Path $Usb) { Remove-Item $Usb -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Usb | Out-Null
Copy-Item "dist\ELintelligence.exe" "$Usb\ELintelligence.exe"
New-Item -ItemType File -Force -Path "$Usb\PORTABLE.flag" | Out-Null
New-Item -ItemType Directory -Force -Path "$Usb\data" | Out-Null
@"
ELintelligence USB Portable

PORTABLE.flag keeps models, runtime, RAG index, chat and settings inside this folder.
Do not publish or share the populated data folder: it may contain personal documents and local history.
"@ | Set-Content -Encoding UTF8 "$Usb\README_USB.txt"
Write-Host "Pacchetto USB pronto in: $Usb" -ForegroundColor Green
