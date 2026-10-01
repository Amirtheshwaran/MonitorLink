@echo off
cd /d "%~dp0"
title MonitorLink - PC Host Mode

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\pythonw.exe" MonitorLink.py --mode pc
) else (
    start "" pythonw MonitorLink.py --mode pc
)
