@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_workbench.ps1" %*
if errorlevel 1 pause
