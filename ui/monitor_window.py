"""
Dedicated Fullscreen Monitor Window for Laptop.
Minimalist borderless canvas with refined top HUD.
"""

import logging
from PyQt6.QtCore import Qt, QTimer, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QImage, QColor, QFont, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QWidget, QPushButton, QLabel, QHBoxLayout, QFrame
from core.power_manager import PowerManager
from ui.components import StatusDot

logger = logging.getLogger(__name__)


class MonitorWindow(QWidget):
    delink_requested = pyqtSignal(str)

    def __init__(self, host_info: str = "Host PC"):
        super().__init__()
        self.host_info = host_info
        self.current_image: QImage | None = None
        self.fps = 0.0
        self.latency_ms = 0.0

        # Window properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet("background-color: #000000;")

        # Mouse tracking for auto-hide
        self.setMouseTracking(True)
        self.cursor_visible = True
        self.cursor_timer = QTimer(self)
        self.cursor_timer.setInterval(1500)
        self.cursor_timer.timeout.connect(self._hide_cursor)
        self.cursor_timer.start()

        # Minimalist Top HUD
        self._init_hud()

        # Keep display awake
        PowerManager.prevent_sleep()

    def _init_hud(self):
        self.hud_container = QFrame(self)
        self.hud_container.setObjectName("MonitorHUD")
        self.hud_container.setStyleSheet("""
            QFrame#MonitorHUD {
                background: rgba(14, 15, 18, 0.94);
                border: 1px solid #272a33;
                border-radius: 8px;
                padding: 4px 12px;
            }
        """)

        layout = QHBoxLayout(self.hud_container)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(14)

        # Status dot
        self.dot = StatusDot("live", self.hud_container)
        layout.addWidget(self.dot)

        self.info_label = QLabel(self.host_info, self.hud_container)
        self.info_label.setStyleSheet("color: #f4f4f5; font-weight: 600; font-size: 12px;")
        layout.addWidget(self.info_label)

        self.stats_label = QLabel("60 FPS • 8ms", self.hud_container)
        self.stats_label.setStyleSheet("color: #71717a; font-size: 11px; font-family: monospace;")
        layout.addWidget(self.stats_label)

        self.delink_btn = QPushButton("Disconnect", self.hud_container)
        self.delink_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delink_btn.setStyleSheet("""
            QPushButton {
                background-color: #272a33;
                color: #f4f4f5;
                font-weight: 500;
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 5px;
                border: 1px solid #363a45;
            }
            QPushButton:hover {
                background-color: #dc2626;
                border-color: #ef4444;
                color: #ffffff;
            }
        """)
        self.delink_btn.clicked.connect(self._on_delink_click)
        layout.addWidget(self.delink_btn)

        esc_hint = QLabel("Esc", self.hud_container)
        esc_hint.setStyleSheet("""
            background: #1e2026;
            color: #71717a;
            font-size: 10px;
            padding: 2px 5px;
            border-radius: 3px;
            border: 1px solid #2a2d36;
        """)
        layout.addWidget(esc_hint)

        self.hud_timer = QTimer(self)
        self.hud_timer.setInterval(2200)
        self.hud_timer.timeout.connect(self._hide_hud)
        self.hud_timer.start()

    def update_frame(self, image: QImage):
        self.current_image = image
        self.update()

    def update_stats(self, fps: float, latency_ms: float):
        self.fps = fps
        self.latency_ms = latency_ms
        self.stats_label.setText(f"{fps:.0f} FPS • {latency_ms:.0f}ms")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        if self.current_image and not self.current_image.isNull():
            img_size = self.current_image.size()
            win_size = self.size()

            scale_w = win_size.width() / img_size.width()
            scale_h = win_size.height() / img_size.height()
            scale = min(scale_w, scale_h)

            target_w = int(img_size.width() * scale)
            target_h = int(img_size.height() * scale)
            target_x = (win_size.width() - target_w) // 2
            target_y = (win_size.height() - target_h) // 2

            target_rect = QRect(target_x, target_y, target_w, target_h)
            painter.drawImage(target_rect, self.current_image)
        else:
            painter.setPen(QColor(113, 113, 122))
            painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Waiting for video signal...")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.hud_container.sizeHint().width()
        h = self.hud_container.sizeHint().height()
        x = (self.width() - w) // 2
        self.hud_container.setGeometry(x, 12, w, h)

    def mouseMoveEvent(self, event: QMouseEvent):
        self._show_cursor()
        self._show_hud()
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self._on_delink_click()
        else:
            super().keyPressEvent(event)

    def _show_cursor(self):
        if not self.cursor_visible:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.cursor_visible = True
        self.cursor_timer.start()

    def _hide_cursor(self):
        if self.cursor_visible:
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.cursor_visible = False

    def _show_hud(self):
        self.hud_container.show()
        self.hud_timer.start()

    def _hide_hud(self):
        self.hud_container.hide()

    def _on_delink_click(self):
        logger.info("Disconnect clicked in monitor window")
        self.delink_requested.emit("user_hud_delink")
        self.close_monitor()

    def close_monitor(self):
        PowerManager.allow_sleep()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.close()

    def closeEvent(self, event):
        PowerManager.allow_sleep()
        super().closeEvent(event)
