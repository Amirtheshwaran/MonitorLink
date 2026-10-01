@echo off
title Installing MonitorLink Virtual Display Driver
echo ========================================================
echo Installing Virtual Display Driver for Windows 10/11
echo ========================================================
echo.

:: 1. Install driver certificate to Trusted Stores
echo [1/3] Adding certificate to Root and Trusted Publishers...
certutil -addstore -f root "C:\Users\Amirthesh\Desktop\Monitor software\driver\VirtualDisplayDriver\Virtual_Display_Driver.cer" >nul 2>&1
certutil -addstore -f TrustedPublisher "C:\Users\Amirthesh\Desktop\Monitor software\driver\VirtualDisplayDriver\Virtual_Display_Driver.cer" >nul 2>&1

:: 2. Install device and driver using NefCon
echo [2/3] Registering Virtual Display device...
if exist "C:\Users\Amirthesh\Desktop\Monitor software\driver\nefcon\x64\nefconw.exe" (
    "C:\Users\Amirthesh\Desktop\Monitor software\driver\nefcon\x64\nefconw.exe" install "C:\Users\Amirthesh\Desktop\Monitor software\driver\VirtualDisplayDriver\MttVDD.inf" "Root\MttVDD"
) else (
    pnputil /add-driver "C:\Users\Amirthesh\Desktop\Monitor software\driver\VirtualDisplayDriver\MttVDD.inf" /install
)

:: 3. Scan for hardware changes
echo [3/3] Scanning for display changes...
pnputil /scan-devices >nul 2>&1

echo.
echo ========================================================
echo Virtual Display Driver installation completed!
echo You can now use Windows Settings to arrange your screens.
echo ========================================================
timeout /t 5
