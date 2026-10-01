"""
Power Management Module for Windows.
Prevents the laptop/screen from going to sleep while acting as a secondary monitor,
and restores normal power settings upon delinking.
"""

import ctypes
import logging

logger = logging.getLogger(__name__)

# Windows Execution State Flags
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_USER_PRESENT = 0x00000004
ES_AWAYMODE_REQUIRED = 0x00000040
ES_CONTINUOUS = 0x80000000


class PowerManager:
    _is_preventing = False

    @classmethod
    def prevent_sleep(cls) -> bool:
        """Keep the system and display awake continuously."""
        try:
            kernel32 = ctypes.windll.kernel32
            res = kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            cls._is_preventing = True
            logger.info("Prevent sleep mode activated (Display & System kept awake)")
            return res != 0
        except Exception as e:
            logger.error(f"Failed to set thread execution state: {e}")
            return False

    @classmethod
    def allow_sleep(cls) -> bool:
        """Restore normal Windows sleep and display timeout behavior."""
        try:
            kernel32 = ctypes.windll.kernel32
            res = kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            cls._is_preventing = False
            logger.info("Normal sleep mode restored")
            return res != 0
        except Exception as e:
            logger.error(f"Failed to restore thread execution state: {e}")
            return False

    @classmethod
    def is_preventing(cls) -> bool:
        return cls._is_preventing
