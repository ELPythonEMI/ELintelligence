@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\MIGRA_DA_PC_A_USB.ps1"
pause
