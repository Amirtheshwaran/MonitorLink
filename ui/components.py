"""
Bespoke UI Components for MonitorLink.
Vector-drawn icons, clean status dots, and native-feeling controls.
"""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout
)


class StatusDot(QWidget):
    """Clean vector-drawn status dot indicator (8px)."""
    def __init__(self, status: str = "idle", parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self.status = status

    def set_status(self, status: str):
        self.status = status
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.status == "live":
            # Emerald green
            color = QColor(16, 185, 129)
        elif self.status == "active":
            # Cobalt blue
            color = QColor(59, 130, 246)
        elif self.status == "warning":
            # Amber
            color = QColor(245, 158, 11)
        else:
            # Muted zinc
            color = QColor(113, 113, 122)

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 8, 8)


class MonitorIcon(QWidget):
    """Vector-drawn minimalist display monitor glyph."""
    def __init__(self, size: int = 36, active: bool = False, parent=None):
        super().__init__(parent)
        self.icon_size = size
        self.active = active
        self.setFixedSize(size, size)

    def set_active(self, active: bool):
        self.active = active
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        accent = QColor(59, 130, 246) if self.active else QColor(113, 113, 122)
        base = QColor(24, 26, 32)

        w = self.width()
        h = self.height()
        sw = w - 6
        sh = int(h * 0.58)
        sx = 3
        sy = 3

        # Screen frame
        painter.setPen(QPen(accent, 1.5))
        painter.setBrush(QBrush(base))
        painter.drawRoundedRect(QRectF(sx, sy, sw, sh), 3, 3)

        # Stand stem
        stem_w = 3
        stem_h = int(h * 0.18)
        stem_x = (w - stem_w) / 2
        stem_y = sy + sh
        painter.setBrush(QBrush(accent))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRectF(stem_x, stem_y, stem_w, stem_h))

        # Stand base
        foot_w = int(w * 0.44)
        foot_h = 2
        foot_x = (w - foot_w) / 2
        foot_y = stem_y + stem_h
        painter.drawRoundedRect(QRectF(foot_x, foot_y, foot_w, foot_h), 1, 1)


class DeviceCard(QFrame):
    """Refined device status card that looks like native hardware pairing."""
    def __init__(self, name: str = "", ip: str = "", connection_type: str = "Wi-Fi", parent=None):
        super().__init__(parent)
        self.setObjectName("DeviceCard")
        self.setStyleSheet("""
            QFrame#DeviceCard {
                background-color: #131418;
                border: 1px solid #20222a;
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        # Category tag
        top_row = QHBoxLayout()
        self.category_label = QLabel("TARGET DISPLAY", self)
        self.category_label.setStyleSheet("color: #52525b; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        top_row.addWidget(self.category_label)
        top_row.addStretch()

        # Badge pill
        self.badge_frame = QFrame(self)
        self.badge_frame.setStyleSheet("""
            background-color: #1a1c23;
            border: 1px solid #282b36;
            border-radius: 11px;
            padding: 3px 10px;
        """)
        badge_layout = QHBoxLayout(self.badge_frame)
        badge_layout.setContentsMargins(8, 2, 8, 2)
        badge_layout.setSpacing(6)

        self.dot = StatusDot(status="live" if name else "idle", parent=self.badge_frame)
        self.status_text = QLabel("Available" if name else "Listening", self.badge_frame)
        self.status_text.setStyleSheet("color: #a1a1aa; font-size: 11px; font-weight: 500;")
        badge_layout.addWidget(self.dot)
        badge_layout.addWidget(self.status_text)
        top_row.addWidget(self.badge_frame)


        card_layout.addLayout(top_row)

        # Device details row
        device_row = QHBoxLayout()
        device_row.setSpacing(14)

        self.icon_widget = MonitorIcon(size=38, active=bool(name), parent=self)
        device_row.addWidget(self.icon_widget)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        self.name_label = QLabel(name or "Searching for nearby devices...", self)
        self.name_label.setStyleSheet("font-weight: 600; color: #f4f4f5; font-size: 14px;")

        self.sub_label = QLabel(f"{connection_type} • {ip}" if ip else "Make sure MonitorLink is open on your other machine", self)
        self.sub_label.setStyleSheet("color: #71717a; font-size: 12px;")

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.sub_label)
        device_row.addLayout(info_layout)
        device_row.addStretch()

        card_layout.addLayout(device_row)

    def set_device(self, name: str, ip: str, connection_type: str = "Wi-Fi"):
        self.icon_widget.set_active(True)
        self.name_label.setText(name)
        self.sub_label.setText(f"{connection_type} • {ip} • Ready")
        self.dot.set_status("live")
        self.status_text.setText("Available")

    def set_searching(self, role_needed: str = "device"):
        self.icon_widget.set_active(False)
        self.name_label.setText(f"Searching for {role_needed}...")
        self.sub_label.setText("Make sure MonitorLink is open on your other machine")
        self.dot.set_status("idle")
        self.status_text.setText("Scanning")

    def set_linked(self, name: str, fps: str = "60 FPS"):
        self.icon_widget.set_active(True)
        self.name_label.setText(name)
        self.sub_label.setText(f"Direct DXGI Stream • {fps} • Latency < 10ms")
        self.dot.set_status("active")
        self.status_text.setText("Streaming")
