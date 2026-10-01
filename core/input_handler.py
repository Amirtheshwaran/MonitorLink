"""
Input Handler for Windows.
Supports remote mouse and keyboard event dispatching (passthrough)
and low-level input control.
"""

import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger(__name__)

# Windows API Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x000A
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_I(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("i", INPUT_I),
    ]


class InputHandler:
    @staticmethod
    def send_mouse_move(norm_x: float, norm_y: float, monitor_rect: tuple = None):
        """Move cursor to normalized coordinate (0.0 to 1.0).

        If monitor_rect is given (left, top, right, bottom), moves within that monitor.
        """
        try:
            user32 = ctypes.windll.user32
            if monitor_rect:
                left, top, right, bottom = monitor_rect
                target_x = int(left + norm_x * (right - left))
                target_y = int(top + norm_y * (bottom - top))
            else:
                w = user32.GetSystemMetrics(0)
                h = user32.GetSystemMetrics(1)
                target_x = int(norm_x * w)
                target_y = int(norm_y * h)

            user32.SetCursorPos(target_x, target_y)
        except Exception as e:
            logger.debug(f"Error moving mouse: {e}")

    @staticmethod
    def send_mouse_button(button: str, down: bool):
        """Send mouse button press or release."""
        try:
            flags = 0
            if button == "left":
                flags = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
            elif button == "right":
                flags = MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP
            elif button == "middle":
                flags = MOUSEEVENTF_MIDDLEDOWN if down else MOUSEEVENTF_MIDDLEUP

            if flags:
                inp = INPUT()
                inp.type = INPUT_MOUSE
                inp.i.mi.dwFlags = flags
                ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        except Exception as e:
            logger.debug(f"Error sending mouse button: {e}")

    @staticmethod
    def send_mouse_wheel(delta: int):
        """Send mouse wheel scroll."""
        try:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.i.mi.dwFlags = MOUSEEVENTF_WHEEL
            inp.i.mi.mouseData = int(delta)
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        except Exception as e:
            logger.debug(f"Error sending wheel scroll: {e}")

    @staticmethod
    def send_key(key_code: int, down: bool):
        """Send keyboard key code press or release."""
        try:
            inp = INPUT()
            inp.type = INPUT_KEYBOARD
            inp.i.ki.wVk = key_code
            inp.i.ki.dwFlags = 0 if down else KEYEVENTF_KEYUP
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        except Exception as e:
            logger.debug(f"Error sending key: {e}")
