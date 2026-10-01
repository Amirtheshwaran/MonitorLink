"""
MonitorLink — Main Application Entrypoint.
Launch as:
    python MonitorLink.py
    python MonitorLink.py --mode pc
    python MonitorLink.py --mode laptop
"""

import sys
import os
import argparse
import logging

# Ensure UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MonitorLink")

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow



def main():
    parser = argparse.ArgumentParser(description="MonitorLink - Use Laptop as Secondary Screen")
    parser.add_argument("--mode", choices=["pc", "laptop"], default="pc", help="Initial mode (pc or laptop)")

    args = parser.parse_args()

    # Enable High DPI scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("MonitorLink")
    app.setOrganizationName("MonitorLink")

    window = MainWindow(initial_mode=args.mode)
    window.show()

    logger.info(f"MonitorLink started in mode='{args.mode}'")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
