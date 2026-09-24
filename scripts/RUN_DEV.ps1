$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { py -3 -m venv .venv }
}
$Python = Resolve-Path ".venv\Scripts\python.exe"
& $Python -m pip install -r requirements.txt
& $Python main.py
