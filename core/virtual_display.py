"""
Virtual Display Driver Manager for Windows 10/11.
Manages the IddCx Indirect Display Driver to create true secondary monitors.
"""

import os
import subprocess
import logging
import win32api
import win32con

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER_DIR = os.path.join(BASE_DIR, "driver", "VirtualDisplayDriver")
NEFCON_EXE = os.path.join(BASE_DIR, "driver", "nefcon", "x64", "nefconw.exe")


class VirtualDisplayManager:
    @staticmethod
    def get_all_displays() -> list[dict]:
        """List all active Windows display monitors in exact Windows Display Settings order."""
        displays = []
        try:
            # Query Windows Desktop Monitor topology order
            monitor_order = {}
            try:
                for m_idx, (hmon, hdc, rect) in enumerate(win32api.EnumDisplayMonitors()):
                    info = win32api.GetMonitorInfo(hmon)
                    dev_name = info.get("Device")
                    if dev_name:
                        monitor_order[dev_name] = {
                            "order": m_idx,
                            "rect": rect,
                            "is_primary": bool(info.get("Flags", 0) & 1),
                        }
            except Exception as e:
                logger.debug(f"EnumDisplayMonitors error: {e}")

            for i in range(64):
                try:
                    dev = win32api.EnumDisplayDevices(None, i)
                    if not dev:
                        continue
                    if dev.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
                        settings = win32api.EnumDisplaySettings(dev.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
                        is_primary = bool(dev.StateFlags & win32con.DISPLAY_DEVICE_PRIMARY_DEVICE)
                        m_info = monitor_order.get(dev.DeviceName, {})
                        sort_key = m_info.get("order", 99 if not is_primary else -1)

                        w = settings.PelsWidth if settings else 1920
                        h = settings.PelsHeight if settings else 1080
                        freq = settings.DisplayFrequency if settings else 60
                        x = settings.Position_x if settings else m_info.get("rect", [0, 0, 0, 0])[0]
                        y = settings.Position_y if settings else m_info.get("rect", [0, 0, 0, 0])[1]

                        displays.append({
                            "device_name": dev.DeviceName,
                            "friendly_name": dev.DeviceString,
                            "is_primary": is_primary or m_info.get("is_primary", False),
                            "width": w,
                            "height": h,
                            "frequency": freq,
                            "x": x,
                            "y": y,
                            "_sort_key": sort_key,
                        })
                except Exception:
                    continue

            # Sort matching Windows Display Settings order (Primary first, then monitor order 2, 3...)
            displays.sort(key=lambda d: (0 if d.get("is_primary") else 1, d.get("_sort_key", 99), d.get("x", 0)))
            for idx, d in enumerate(displays):
                d["index"] = idx
                d.pop("_sort_key", None)

        except Exception as e:
            logger.error(f"Error enumerating displays: {e}")

        # Fallback to single primary monitor if enumeration fails
        if not displays:
            w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            displays.append({
                "index": 0,
                "device_name": r"\\.\DISPLAY1",
                "friendly_name": "Primary Display",
                "is_primary": True,
                "width": w,
                "height": h,
                "frequency": 60,
                "x": 0,
                "y": 0,
            })
        return displays

    @staticmethod
    def is_driver_installed() -> bool:
        """Check if Virtual Display Driver / IddSampleDriver is present in Windows PnP devices."""
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-PnpDevice -Class Display -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -like '*Virtual Display*' -or $_.FriendlyName -like '*IddSampleDriver*' } | Measure-Object | Select-Object -ExpandProperty Count"
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            count = int(proc.stdout.strip() or "0")
            return count > 0
        except Exception as e:
            logger.debug(f"Error checking driver install status: {e}")
            return False

    @staticmethod
    def is_virtual_display_active() -> bool:
        """Check if the virtual display is currently enabled and active."""
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-PnpDevice -Class Display -ErrorAction SilentlyContinue | Where-Object { ($_.FriendlyName -like '*Virtual Display*' -or $_.FriendlyName -like '*IddSampleDriver*') -and $_.Status -eq 'OK' } | Measure-Object | Select-Object -ExpandProperty Count"
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            count = int(proc.stdout.strip() or "0")
            return count > 0
        except Exception as e:
            logger.debug(f"Error checking virtual display active status: {e}")
            return False

    @staticmethod
    def install_driver() -> tuple[bool, str]:
        """Installs the Virtual Display Driver with certificate via an elevated PowerShell process."""
        script_path = os.path.join(BASE_DIR, "install_driver.bat")
        if not os.path.exists(script_path):
            VirtualDisplayManager.create_install_script()

        # Run elevated
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Start-Process -FilePath '{script_path}' -Verb RunAs -Wait"
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if VirtualDisplayManager.is_driver_installed():
                return True, "Virtual Display Driver installed successfully!"
            else:
                return False, "Driver installation completed, but virtual device not yet detected. A system restart may be required."
        except Exception as e:
            return False, f"Failed to launch installer: {e}"

    @staticmethod
    def toggle_virtual_display(enable: bool) -> tuple[bool, str]:
        """Enables or disables the virtual display device."""
        action = "enable-pnpdevice -Confirm:$false" if enable else "disable-pnpdevice -Confirm:$false"
        ps_code = f"""
        $dev = Get-PnpDevice -Class Display -ErrorAction SilentlyContinue | Where-Object {{ $_.FriendlyName -like '*Virtual Display*' -or $_.FriendlyName -like '*IddSampleDriver*' }};
        if ($dev) {{
            $dev | {action};
            Write-Output 'OK'
        }} else {{
            Write-Output 'NOT_FOUND'
        }}
        """
        # Execute elevated if needed
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Start-Process -FilePath powershell.exe -ArgumentList '-NoProfile', '-Command', '{ps_code}' -Verb RunAs -Wait"
        ]
        try:
            subprocess.run(cmd, timeout=30)
            state = "enabled" if enable else "disabled"
            return True, f"Virtual display successfully {state}!"
        except Exception as e:
            return False, f"Error toggling display: {e}"

    @staticmethod
    def open_display_settings():
        """Open Windows Display Settings so user can arrange monitors."""
        try:
            os.system("start ms-settings:display")
        except Exception as e:
            logger.error(f"Failed to open display settings: {e}")

    @staticmethod
    def create_install_script():
        """Creates the self-contained install_driver.bat script."""
        script_path = os.path.join(BASE_DIR, "install_driver.bat")
        cat_file = os.path.join(DRIVER_DIR, "mttvdd.cat")
        cer_file = os.path.join(DRIVER_DIR, "Virtual_Display_Driver.cer")
        inf_file = os.path.join(DRIVER_DIR, "MttVDD.inf")
        
        content = f"""@echo off
title Installing MonitorLink Virtual Display Driver
echo ========================================================
echo Installing Virtual Display Driver for Windows 10/11
echo ========================================================
echo.

:: 1. Install driver certificate to Trusted Stores
echo [1/3] Adding certificate to Root and Trusted Publishers...
certutil -addstore -f root "{cer_file}" >nul 2>&1
certutil -addstore -f TrustedPublisher "{cer_file}" >nul 2>&1

:: 2. Install device and driver using NefCon
echo [2/3] Registering Virtual Display device...
if exist "{NEFCON_EXE}" (
    "{NEFCON_EXE}" install "{inf_file}" "Root\\MttVDD"
) else (
    pnputil /add-driver "{inf_file}" /install
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
"""
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(content)


VirtualDisplayManager.create_install_script()
