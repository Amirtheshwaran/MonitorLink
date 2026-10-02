"""
MonitorLink — Clean Professional Desktop Interface.
Designed with subtle neutral surfaces, crisp borders, and zero AI-slop tropes.
"""

import json
import logging
import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QDialog, QTabWidget, QFrame,
    QMessageBox, QComboBox
)

from core.virtual_display import VirtualDisplayManager
from core.streamer import HostStreamer
from core.receiver import StreamReceiver
from core.discovery import DiscoveryService, get_local_ip_addresses
from core.power_manager import PowerManager
from ui.components import StatusDot, MonitorIcon, DeviceCard
from ui.monitor_window import MonitorWindow
from ui.styles import PRO_THEME_QSS

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"role": "pc", "quality": 75, "fps": 60, "source_idx": 0}


def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to save config: {e}")


class SettingsDialog(QDialog):
    """Clean utilitarian settings dialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings & Drivers")
        self.resize(540, 440)
        self.setStyleSheet(PRO_THEME_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        tabs = QTabWidget(self)
        layout.addWidget(tabs)

        # Tab 1: Virtual Display Driver
        vdd_tab = QWidget()
        v_layout = QVBoxLayout(vdd_tab)
        v_layout.setContentsMargins(16, 16, 16, 16)
        v_layout.setSpacing(12)

        lbl = QLabel("<b>Windows Virtual Display Driver (IddCx)</b><br>Adds an independent extended monitor in Windows Display Settings.", self)
        lbl.setStyleSheet("color: #d4d4d8; font-size: 12px; line-height: 1.4;")
        v_layout.addWidget(lbl)

        self.btn_install = QPushButton("Install Virtual Display Driver (Admin)", self)
        self.btn_install.setProperty("class", "PrimaryActionBtn")
        self.btn_install.clicked.connect(self._install_driver)
        v_layout.addWidget(self.btn_install)

        h_box = QHBoxLayout()
        def _toggle_and_refresh(enable: bool):
            VirtualDisplayManager.toggle_virtual_display(enable)
            if parent and hasattr(parent, "_refresh_display_list"):
                QTimer.singleShot(800, parent._refresh_display_list)

        btn_en = QPushButton("Enable Virtual Screen", self)
        btn_en.setProperty("class", "GhostBtn")
        btn_en.clicked.connect(lambda: _toggle_and_refresh(True))

        btn_dis = QPushButton("Disable Virtual Screen", self)
        btn_dis.setProperty("class", "GhostBtn")
        btn_dis.clicked.connect(lambda: _toggle_and_refresh(False))

        h_box.addWidget(btn_en)
        h_box.addWidget(btn_dis)
        v_layout.addLayout(h_box)

        btn_win = QPushButton("Open Windows Display Settings", self)
        btn_win.setProperty("class", "GhostBtn")
        btn_win.clicked.connect(VirtualDisplayManager.open_display_settings)
        v_layout.addWidget(btn_win)

        v_layout.addStretch()
        tabs.addTab(vdd_tab, "Virtual Display Driver")

        # Tab 2: Connection Guide
        guide_tab = QWidget()
        g_layout = QVBoxLayout(guide_tab)
        g_layout.setContentsMargins(16, 16, 16, 16)
        g_text = QLabel(
            "<b>Wireless (Wi-Fi):</b><br>"
            "Ensure both devices are on the same Wi-Fi network. Discovery and pairing are automatic.<br><br>"
            "<b>Wired (Direct Ethernet / USB-C):</b><br>"
            "Connect an Ethernet or USB data cable directly between machines for sub-5ms gigabit streaming.<br><br>"
            "<b>Hardware Note regarding Laptop HDMI Ports:</b><br>"
            "Laptop HDMI ports are video outputs only (they send video to monitors, cannot receive incoming signals). "
            "Use Wi-Fi, direct Ethernet cable, or a standard USB HDMI capture dongle.",
            self
        )
        g_text.setWordWrap(True)
        g_text.setStyleSheet("color: #a1a1aa; font-size: 12px; line-height: 1.5;")
        g_layout.addWidget(g_text)
        g_layout.addStretch()
        tabs.addTab(guide_tab, "Connection Guide")

        btn_close = QPushButton("Done", self)
        btn_close.setProperty("class", "GhostBtn")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _install_driver(self):
        success, msg = VirtualDisplayManager.install_driver()
        if success:
            QMessageBox.information(self, "Driver", msg)
        else:
            QMessageBox.warning(self, "Driver", msg)


class MainWindow(QMainWindow):
    def __init__(self, initial_mode: str = "pc"):
        super().__init__()
        self.setWindowTitle("MonitorLink")
        self.setFixedSize(480, 440)
        self.setStyleSheet(PRO_THEME_QSS)


        # Config & Role
        self.cfg = load_config()
        self.current_role = initial_mode or self.cfg.get("role", "pc")

        # Connection State
        self.is_linked = False
        self.discovered_peers = {}
        self.target_peer_ip = ""
        self.target_peer_name = ""

        # Background Services
        self.host_streamer: HostStreamer | None = None
        self.receiver_client: StreamReceiver | None = None
        self.monitor_window: MonitorWindow | None = None
        self.discovery: DiscoveryService | None = None

        self._init_ui()
        self._init_services()

        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self._update_discovery_ui)
        self.update_timer.start()

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(22, 20, 22, 20)
        main_layout.setSpacing(16)

        # Header bar
        header = QHBoxLayout()
        header.setSpacing(10)

        # App brand
        icon_brand = MonitorIcon(size=22, active=True, parent=self)
        header.addWidget(icon_brand)

        title_lbl = QLabel("MonitorLink", self)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #f4f4f5; letter-spacing: -0.2px;")
        header.addWidget(title_lbl)

        version_lbl = QLabel("v1.0", self)
        version_lbl.setStyleSheet("font-size: 10px; color: #52525b; font-weight: 600; padding-top: 2px;")
        header.addWidget(version_lbl)

        header.addStretch()

        self.btn_settings = QPushButton("Settings", self)
        self.btn_settings.setProperty("class", "GhostBtn")
        self.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings.clicked.connect(self._open_settings)
        header.addWidget(self.btn_settings)

        main_layout.addLayout(header)

        # Segmented Control (Sender PC vs Receiver Laptop)
        seg_frame = QFrame(self)
        seg_frame.setObjectName("SegmentTrack")
        seg_layout = QHBoxLayout(seg_frame)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(4)

        self.btn_role_pc = QPushButton("Sender (PC)", self)
        self.btn_role_pc.setProperty("class", "SegmentBtn")
        self.btn_role_pc.setCheckable(True)
        self.btn_role_pc.setChecked(self.current_role == "pc")
        self.btn_role_pc.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_role_pc.clicked.connect(lambda: self._set_role("pc"))

        self.btn_role_laptop = QPushButton("Receiver (Laptop)", self)
        self.btn_role_laptop.setProperty("class", "SegmentBtn")
        self.btn_role_laptop.setCheckable(True)
        self.btn_role_laptop.setChecked(self.current_role == "laptop")
        self.btn_role_laptop.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_role_laptop.clicked.connect(lambda: self._set_role("laptop"))

        seg_layout.addWidget(self.btn_role_pc)
        seg_layout.addWidget(self.btn_role_laptop)
        main_layout.addWidget(seg_frame)

        # Hardware / Device Status Card
        self.device_card = DeviceCard(parent=self)
        main_layout.addWidget(self.device_card)

        # Display Source Selector (visible when role == "pc")
        self.display_row = QWidget(self)
        disp_layout = QHBoxLayout(self.display_row)
        disp_layout.setContentsMargins(4, 0, 4, 0)
        disp_layout.setSpacing(8)

        disp_lbl = QLabel("STREAM DISPLAY:", self.display_row)
        disp_lbl.setStyleSheet("color: #71717a; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        disp_layout.addWidget(disp_lbl)

        self.display_combo = QComboBox(self.display_row)
        self.display_combo.setFixedHeight(30)
        self.display_combo.setStyleSheet("""
            QComboBox {
                background-color: #181a20;
                color: #e4e4e7;
                border: 1px solid #282b36;
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #181a20;
                color: #f4f4f5;
                selection-background-color: #27272a;
                border: 1px solid #282b36;
                outline: none;
            }
        """)
        self.display_combo.currentIndexChanged.connect(self._on_display_selected)
        disp_layout.addWidget(self.display_combo, 1)

        self.btn_refresh_displays = QPushButton("↻", self.display_row)
        self.btn_refresh_displays.setFixedSize(30, 30)
        self.btn_refresh_displays.setProperty("class", "GhostBtn")
        self.btn_refresh_displays.setToolTip("Refresh connected displays")
        self.btn_refresh_displays.clicked.connect(self._refresh_display_list)
        disp_layout.addWidget(self.btn_refresh_displays)

        main_layout.addWidget(self.display_row)
        self.display_row.setVisible(self.current_role == "pc")
        self._refresh_display_list()

        # Main Action Button (Connect / Disconnect)
        self.btn_action = QPushButton("Connect Display", self)
        self.btn_action.setFixedHeight(46)
        self.btn_action.setProperty("class", "PrimaryActionBtn")
        self.btn_action.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_action.clicked.connect(self._on_action_clicked)
        main_layout.addWidget(self.btn_action)

        # Bottom subtle meta
        self.meta_label = QLabel("Direct DXGI Hardware Capture • 60 FPS", self)
        self.meta_label.setStyleSheet("color: #52525b; font-size: 11px;")
        self.meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.meta_label)

    def _set_role(self, role: str):
        if self.is_linked:
            self._do_delink()

        self.current_role = role
        self.cfg["role"] = role
        save_config(self.cfg)

        self.btn_role_pc.setChecked(role == "pc")
        self.btn_role_laptop.setChecked(role == "laptop")
        self.display_row.setVisible(role == "pc")
        if role == "pc":
            self._refresh_display_list()
        self._restart_services()

    def _init_services(self):
        self.discovery = DiscoveryService(
            role=self.current_role,
            service_port=8765
        )
        self.discovery.device_found.connect(self._on_peer_found)
        self.discovery.device_lost.connect(self._on_peer_lost)
        self.discovery.start()

        if self.current_role == "pc":
            self._start_host_service()
        else:
            self._start_standby_receiver_service()

    def _restart_services(self):
        if self.host_streamer:
            self.host_streamer.stop()
            self.host_streamer = None
        if self.receiver_client:
            self.receiver_client.stop()
            self.receiver_client = None
        if self.discovery:
            self.discovery.role = self.current_role

        if self.current_role == "pc":
            self._start_host_service()
        else:
            self._start_standby_receiver_service()
        self._update_discovery_ui()

    def _start_host_service(self):
        displays = VirtualDisplayManager.get_all_displays()
        preferred = 1 if len(displays) > 1 else 0
        source_idx = self.cfg.get("source_idx", preferred)
        if source_idx >= len(displays):
            source_idx = preferred

        self.host_streamer = HostStreamer(
            port=8765,
            target_fps=60,
            quality=self.cfg.get("quality", 85)
        )
        self.host_streamer.client_connected.connect(self._on_client_linked)
        self.host_streamer.client_disconnected.connect(self._on_client_unlinked)
        self.host_streamer.delink_received.connect(self._on_remote_delink)
        self.host_streamer.set_source_display(source_idx)
        self.host_streamer.start()

    def _refresh_display_list(self):
        if not hasattr(self, "display_combo"):
            return
        self.display_combo.blockSignals(True)
        self.display_combo.clear()
        displays = VirtualDisplayManager.get_all_displays()
        best_idx = 0
        for i, d in enumerate(displays):
            is_prim = d.get("is_primary", False)
            w = d.get("width", 1920)
            h = d.get("height", 1080)
            label = f"Display {i+1}: {w}x{h} ({'Primary Screen' if is_prim else 'Extended / Virtual'})"
            self.display_combo.addItem(label, i)
            if not is_prim and best_idx == 0:
                best_idx = i

        chosen_idx = self.cfg.get("source_idx", best_idx)
        if chosen_idx >= len(displays):
            chosen_idx = best_idx
        self.display_combo.setCurrentIndex(chosen_idx)
        self.display_combo.blockSignals(False)

    def _on_display_selected(self, combo_idx: int):
        target_display_idx = self.display_combo.currentData()
        if target_display_idx is None:
            target_display_idx = combo_idx
        self.cfg["source_idx"] = target_display_idx
        save_config(self.cfg)
        if self.host_streamer:
            self.host_streamer.set_source_display(target_display_idx)

    def _start_standby_receiver_service(self):
        pass

    def _connect_standby_receiver(self, ip: str):
        if self.receiver_client:
            if self.receiver_client._running and self.receiver_client.host == ip:
                return
            self.receiver_client.stop()
            self.receiver_client = None

        self.receiver_client = StreamReceiver(host=ip, port=8765)
        self.receiver_client.activate_requested.connect(self._on_activate_monitor_cmd)
        self.receiver_client.delink_received.connect(self._on_remote_delink)
        self.receiver_client.frame_ready.connect(self._on_frame_received)
        self.receiver_client.stats_updated.connect(self._on_receiver_stats)
        self.receiver_client.start()

    def _on_action_clicked(self):
        if not self.is_linked:
            self._do_link()
        else:
            self._do_delink()

    def _do_link(self):
        if self.current_role == "pc":
            if self.host_streamer:
                self.host_streamer.trigger_link()
            self.is_linked = True
            self._set_ui_linked(True)
        else:
            ip = self.target_peer_ip
            if not ip or ip == "127.0.0.1":
                from PyQt6.QtWidgets import QInputDialog
                last_ip = self.cfg.get("last_pc_ip", "")
                text, ok = QInputDialog.getText(
                    self,
                    "Connect to PC Host",
                    "Enter Host PC IP Address (e.g. 172.20.x.x):",
                    text=last_ip
                )
                if ok and text.strip():
                    ip = text.strip()
                    self.target_peer_ip = ip
                    self.target_peer_name = f"PC ({ip})"
                    self.cfg["last_pc_ip"] = ip
                    save_config(self.cfg)
                else:
                    return

            self._connect_standby_receiver(ip)
            if self.receiver_client:
                self.receiver_client.send_link_request()
            self._open_laptop_monitor()

    def _do_delink(self):
        if self.current_role == "pc":
            if self.host_streamer:
                self.host_streamer.delink_all(reason="pc_user_delink")
        else:
            if self.receiver_client:
                self.receiver_client.send_delink("laptop_user_delink")
            self._close_laptop_monitor()

        self.is_linked = False
        self._set_ui_linked(False)

    def _on_remote_delink(self, reason: str):
        self.is_linked = False
        if self.current_role == "laptop":
            self._close_laptop_monitor()
        self._set_ui_linked(False)

    def _on_client_linked(self, addr):
        if self.current_role == "pc":
            self.is_linked = True
            self._set_ui_linked(True)

    def _on_client_unlinked(self, addr):
        if self.current_role == "pc" and self.is_linked:
            self.is_linked = False
            self._set_ui_linked(False)

    def _on_activate_monitor_cmd(self):
        self._open_laptop_monitor()

    def _open_laptop_monitor(self):
        if not self.monitor_window:
            self.monitor_window = MonitorWindow(host_info=self.target_peer_name or "PC Host")
            self.monitor_window.delink_requested.connect(self._do_delink)
            if self.receiver_client:
                self.receiver_client.frame_ready.connect(self.monitor_window.update_frame)
            self.monitor_window.showFullScreen()
            self.is_linked = True
            self._set_ui_linked(True)

    def _close_laptop_monitor(self):
        if self.monitor_window:
            self.monitor_window.close_monitor()
            self.monitor_window = None

    def _on_frame_received(self, img):
        if self.monitor_window:
            self.monitor_window.update_frame(img)

    def _on_receiver_stats(self, fps: float, latency_ms: float):
        if self.monitor_window:
            self.monitor_window.update_stats(fps, latency_ms)

    def _set_ui_linked(self, linked: bool):
        if linked:
            self.device_card.set_linked(
                self.target_peer_name or ("Laptop Screen" if self.current_role == "pc" else "PC Host")
            )
            self.btn_action.setText("Disconnect Display")
            self.btn_action.setProperty("class", "DangerActionBtn")
            self.btn_action.style().unpolish(self.btn_action)
            self.btn_action.style().polish(self.btn_action)
            self.meta_label.setText("Streaming Active • Low Latency")
        else:
            self.btn_action.setText("Connect Display")
            self.btn_action.setProperty("class", "PrimaryActionBtn")
            self.btn_action.style().unpolish(self.btn_action)
            self.btn_action.style().polish(self.btn_action)
            self.meta_label.setText("Direct DXGI Hardware Capture • 60 FPS")
            self._update_discovery_ui()

    def _on_peer_found(self, peer: dict):
        key = f"{peer.get('ip')}:{peer.get('port')}"
        self.discovered_peers[key] = peer
        peer_role = peer.get("role", "")
        if self.current_role == "laptop" and peer_role in ("pc", "host", "sender", "both") and not self.is_linked:
            self.target_peer_ip = peer.get("ip")
            self.target_peer_name = peer.get("hostname", "PC Host")
            self._connect_standby_receiver(self.target_peer_ip)

    def _on_peer_lost(self, peer: dict):
        key = f"{peer.get('ip')}:{peer.get('port')}"
        self.discovered_peers.pop(key, None)

    def _update_discovery_ui(self):
        if self.is_linked:
            return

        target_roles = ("laptop", "receiver", "client") if self.current_role == "pc" else ("pc", "host", "sender")
        matching_peers = [p for p in self.discovered_peers.values() if p.get("role") in target_roles or p.get("role") == "both"]

        # Prioritize routable LAN/Wi-Fi addresses over link-local APIPA (169.254.x.x)
        matching_peers.sort(key=lambda p: (1 if p.get("ip", "").startswith("169.254.") else 0, p.get("ip", "")))

        if matching_peers:
            peer = matching_peers[0]
            self.target_peer_ip = peer.get("ip")
            self.target_peer_name = peer.get("hostname", "Device")
            self.device_card.set_device(
                name=self.target_peer_name,
                ip=self.target_peer_ip,
                connection_type=peer.get("network_type", "Wi-Fi")
            )
            self.btn_action.setEnabled(True)
        else:
            role_needed = "Laptop" if self.current_role == "pc" else "PC Host"
            self.device_card.set_searching(role_needed)
            self.btn_action.setEnabled(True)

    def _open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        if self.is_linked:
            self._do_delink()
        if self.host_streamer:
            self.host_streamer.stop()
        if self.receiver_client:
            self.receiver_client.stop()
        if self.discovery:
            self.discovery.stop()
        PowerManager.allow_sleep()
        super().closeEvent(event)
