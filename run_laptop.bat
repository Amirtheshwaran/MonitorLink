@echo off
cd /d "%~dp0"
title MonitorLink - Laptop Display Mode

if exist "MonitorLink.exe" (
    start "" "MonitorLink.exe" --mode laptop
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\pythonw.exe" MonitorLink.py --mode laptop
) else (
    start "" pythonw MonitorLink.py --mode laptop
)
