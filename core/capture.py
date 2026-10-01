import ctypes
import os
import time
import logging

logger = logging.getLogger(__name__)

_GLOBAL_DESKTOP_HANDLE = None

def ensure_input_desktop():
    """Ensure the calling thread is attached to the interactive input desktop."""
    global _GLOBAL_DESKTOP_HANDLE
    try:
        user32 = ctypes.windll.user32
        if _GLOBAL_DESKTOP_HANDLE is None:
            _GLOBAL_DESKTOP_HANDLE = user32.OpenInputDesktop(0, False, 0x01FF)
        if _GLOBAL_DESKTOP_HANDLE:
            user32.SetThreadDesktop(_GLOBAL_DESKTOP_HANDLE)
    except Exception as e:
        logger.debug(f"Desktop switch notice: {e}")

# Must switch thread desktop before any windowing or COM libraries are initialized
ensure_input_desktop()

import cv2
import numpy as np
import win32gui
import win32ui
import win32con



class ScreenCapture:
    def __init__(self, output_idx: int = 0, target_width: int = 1920, target_height: int = 1080, quality: int = 75):
        self.output_idx = output_idx
        self.target_width = target_width
        self.target_height = target_height
        self.quality = quality
        self.cam = None
        self.use_dxgi = True
        self.running = False
        self._init_dxgi()

    def _init_dxgi(self):
        ensure_input_desktop()
        try:
            import bettercam
            self.cam = bettercam.create(output_idx=self.output_idx, max_buffer_len=2)
            self.use_dxgi = True
            logger.info(f"Initialized DXGI Desktop Duplication on output {self.output_idx}")
        except Exception as e:
            logger.warning(f"DXGI init failed on output {self.output_idx} ({e}), falling back to GDI.")
            self.use_dxgi = False
            self.cam = None

    def grab_frame(self) -> np.ndarray | None:
        """Capture one raw RGB/BGR frame."""
        if self.use_dxgi and self.cam is not None:
            try:
                frame = self.cam.grab()
                if frame is not None:
                    return frame
            except Exception as e:
                logger.debug(f"DXGI grab error: {e}, falling back to GDI")
                self.use_dxgi = False

        # Fallback to Win32 GDI
        return self._grab_gdi()

    def _grab_gdi(self) -> np.ndarray | None:
        try:
            ensure_input_desktop()
            hwnd = win32gui.GetDesktopWindow()
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(saveBitMap)

            saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)

            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))

            # Cleanup DCs
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

            # Return BGR
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            logger.error(f"GDI grab failed: {e}")
            return None

    def capture_compressed_jpeg(self) -> bytes | None:
        """Capture, scale, and JPEG encode a frame ready for network transmission."""
        frame = self.grab_frame()
        if frame is None:
            return None

        h, w = frame.shape[:2]
        if self.target_width > 0 and self.target_height > 0 and (w != self.target_width or h != self.target_height):
            # Scale frame to target resolution
            frame = cv2.resize(frame, (self.target_width, self.target_height), interpolation=cv2.INTER_LINEAR)

        # Encode to JPEG
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality, int(cv2.IMWRITE_JPEG_OPTIMIZE), 0]
        success, encoded = cv2.imencode('.jpg', frame, encode_params)
        if success:
            return encoded.tobytes()
        return None

    def release(self):
        if self.cam is not None:
            try:
                self.cam.release()
            except Exception:
                pass
            self.cam = None


class WindowCapture:
    """Capture a specific application window by HWND."""
    def __init__(self, hwnd: int, target_width: int = 1920, target_height: int = 1080, quality: int = 75):
        self.hwnd = hwnd
        self.target_width = target_width
        self.target_height = target_height
        self.quality = quality

    def grab_frame(self) -> np.ndarray | None:
        try:
            if not win32gui.IsWindow(self.hwnd):
                return None

            left, top, right, bot = win32gui.GetClientRect(self.hwnd)
            w = right - left
            h = bot - top
            if w <= 0 or h <= 0:
                return None

            hwndDC = win32gui.GetDC(self.hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(saveBitMap)

            # PrintWindow PW_RENDERFULLCONTENT = 2
            ctypes.windll.user32.PrintWindow(self.hwnd, saveDC.GetSafeHdc(), 2)

            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))

            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, hwndDC)

            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            logger.error(f"Window grab failed: {e}")
            return None

    def capture_compressed_jpeg(self) -> bytes | None:
        frame = self.grab_frame()
        if frame is None:
            return None

        h, w = frame.shape[:2]
        if self.target_width > 0 and self.target_height > 0 and (w != self.target_width or h != self.target_height):
            frame = cv2.resize(frame, (self.target_width, self.target_height), interpolation=cv2.INTER_LINEAR)

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality, int(cv2.IMWRITE_JPEG_OPTIMIZE), 0]
        success, encoded = cv2.imencode('.jpg', frame, encode_params)
        if success:
            return encoded.tobytes()
        return None

    def release(self):
        pass


def list_open_windows() -> list[dict]:
    """Enumerate top-level visible application windows for streaming."""
    ensure_input_desktop()
    windows = []

    def enum_cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title and title != "Program Manager":
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 100 and h > 100:
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "width": w,
                        "height": h
                    })
        return True

    win32gui.EnumWindows(enum_cb, None)
    return windows
