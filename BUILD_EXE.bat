@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\BUILD_WINDOWS.ps1" -OneFile
if errorlevel 1 pause
endlocal
