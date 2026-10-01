"""
Modern Pro Dark Theme (Linear / Raycast / Windows 11 Inspired).
Focuses on subtle neutral surfaces, crisp borders, refined typography,
and zero tacky neon gradients.
"""

PRO_THEME_QSS = """
/* Global Window */
QMainWindow, QDialog, QWidget#CentralWidget {
    background-color: #0b0c0e;
    color: #f4f4f5;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}

/* Base Panel */
QFrame.PanelFrame {
    background-color: #121316;
    border: 1px solid #1f2127;
    border-radius: 10px;
}

/* Device & Content Cards */
QFrame.CardFrame {
    background-color: #16181d;
    border: 1px solid #22252c;
    border-radius: 8px;
}
QFrame.CardFrame:hover {
    border: 1px solid #2f333d;
}

/* Typography */
QLabel.HeaderTitle {
    font-size: 14px;
    font-weight: 600;
    color: #f4f4f5;
    letter-spacing: -0.2px;
}
QLabel.MutedText {
    font-size: 12px;
    color: #71717a;
}
QLabel.SubText {
    font-size: 11px;
    color: #52525b;
}

/* Segmented Control Track */
QFrame#SegmentTrack {
    background-color: #121316;
    border: 1px solid #1f2127;
    border-radius: 8px;
    padding: 3px;
}
QPushButton.SegmentBtn {
    background-color: transparent;
    color: #71717a;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 16px;
    border-radius: 6px;
    border: none;
}
QPushButton.SegmentBtn:hover {
    color: #e4e4e7;
    background-color: #181a1f;
}
QPushButton.SegmentBtn:checked {
    background-color: #22252c;
    color: #ffffff;
    font-weight: 600;
    border: 1px solid #2e323b;
}

/* Primary Action Buttons */
QPushButton.PrimaryActionBtn {
    background-color: #2563eb;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    padding: 12px 24px;
    border-radius: 8px;
    border: 1px solid #3b82f6;
    letter-spacing: -0.1px;
}
QPushButton.PrimaryActionBtn:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}
QPushButton.PrimaryActionBtn:pressed {
    background-color: #1e40af;
}
QPushButton.PrimaryActionBtn:disabled {
    background-color: #181a1f;
    color: #52525b;
    border: 1px solid #22252c;
}

/* Danger / Delink Buttons */
QPushButton.DangerActionBtn {
    background-color: #b91c1c;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    padding: 12px 24px;
    border-radius: 8px;
    border: 1px solid #dc2626;
}
QPushButton.DangerActionBtn:hover {
    background-color: #991b1b;
    border-color: #ef4444;
}
QPushButton.DangerActionBtn:pressed {
    background-color: #7f1d1d;
}

/* Secondary / Ghost Buttons */
QPushButton.GhostBtn {
    background-color: transparent;
    color: #a1a1aa;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid #22252c;
}
QPushButton.GhostBtn:hover {
    background-color: #181a1f;
    color: #f4f4f5;
    border-color: #2e323b;
}
QPushButton.GhostBtn:pressed {
    background-color: #121316;
}

/* Inputs & Combos */
QLineEdit, QComboBox {
    background-color: #121316;
    color: #f4f4f5;
    border: 1px solid #22252c;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 12px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
    background-color: #14161b;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #16181d;
    color: #f4f4f5;
    border: 1px solid #22252c;
    selection-background-color: #2563eb;
    border-radius: 6px;
    padding: 4px;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #1f2127;
    border-radius: 8px;
    background: #121316;
}
QTabBar::tab {
    background: #0e0f12;
    color: #71717a;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
    font-size: 12px;
    border: 1px solid #1f2127;
    border-bottom: none;
}
QTabBar::tab:selected {
    background: #16181d;
    color: #f4f4f5;
    border-top: 2px solid #3b82f6;
}
QTabBar::tab:hover:!selected {
    background: #121316;
    color: #a1a1aa;
}

/* Sliders */
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #22252c;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: none;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

/* Checkboxes */
QCheckBox {
    color: #d4d4d8;
    font-size: 12px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #27272a;
    background-color: #121316;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
}
"""
