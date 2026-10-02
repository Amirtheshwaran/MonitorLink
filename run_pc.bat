@echo off
cd /d "%~dp0"
title MonitorLink - PC Host Mode

if exist "MonitorLink.exe" (
    start "" "MonitorLink.exe" --mode pc
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\pythonw.exe" MonitorLink.py --mode pc
) else (
    start "" pythonw MonitorLink.py --mode pc
)
