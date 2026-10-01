@echo off
cd /d "%~dp0"
title MonitorLink

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" MonitorLink.py %*
) else (
    python MonitorLink.py %*
)
