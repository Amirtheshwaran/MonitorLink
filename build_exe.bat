@echo off
cd /d "%~dp0"
title Building Standalone MonitorLink Executable
echo ========================================================
echo Building MonitorLink Standalone for Windows
echo ========================================================
echo.

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [ERROR] PyInstaller not found in .venv!
    pause
    exit /b 1
)

echo Packaging into dist\MonitorLink ...
".venv\Scripts\pyinstaller.exe" --noconfirm --onedir --windowed --name "MonitorLink" --add-data "driver;driver" --add-data "static;static" MonitorLink.py

echo.
echo ========================================================
echo Build complete!
echo You can copy the "dist\MonitorLink" folder to your laptop!
echo ========================================================
pause
