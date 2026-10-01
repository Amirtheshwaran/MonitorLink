@echo off
title MonitorLink Setup
cd /d "%~dp0"

echo ========================================================
echo Setting up MonitorLink for this computer...
echo ========================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org or Microsoft Store,
    echo making sure to check "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/2] Creating virtual environment...
python -m venv .venv

echo [2/2] Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo ========================================================
echo Setup complete! You can now run "run.bat"
echo ========================================================
pause
