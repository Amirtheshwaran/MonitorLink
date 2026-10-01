"""
High-Performance Video Receiver Client for Laptop.
Connects to the PC Streamer, decodes binary video frames, tracks latency/FPS,
and handles bidirectional Delink control.
"""

import asyncio
import json
import logging
import threading
import time
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage
import websockets

logger = logging.getLogger(__name__)


class StreamReceiver(QObject):
    # Qt Signals for UI integration
    frame_ready = pyqtSignal(QImage)
    connected = pyqtSignal()
    disconnected = pyqtSignal(str)
    delink_received = pyqtSignal(str)
    activate_requested = pyqtSignal()
    stats_updated = pyqtSignal(float, float)  # (fps, latency_ms)

    def __init__(self, host: str, port: int = 8765):
        super().__init__()
        self.host = host
        self.port = port
        self.stream_url = f"ws://{host}:{port}/stream"
        self.control_url = f"ws://{host}:{port}/control"

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._control_ws = None
        self._stream_ws = None

        self.current_fps = 0.0
        self.current_latency_ms = 0.0
        self.is_connected = False

    def start(self):
        """Connect to host and start receiving frames."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_client, daemon=True)
        self._thread.start()
        logger.info(f"StreamReceiver connecting to {self.stream_url}")

    def stop(self):
        """Disconnect and stop receiver thread."""
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._cleanup(), self._loop)

    def send_link_request(self):
        """Send Link request from laptop to host."""
        if self._control_ws and self._loop and self._loop.is_running():
            msg = json.dumps({"type": "link_request"})
            asyncio.run_coroutine_threadsafe(self._control_ws.send(msg), self._loop)
            logger.info("Sent link request to host")

    def send_delink(self, reason: str = "laptop_user_exit"):
        """Send Delink request from laptop to host."""
        if self._control_ws and self._loop and self._loop.is_running():
            msg = json.dumps({"type": "delink", "reason": reason})
            asyncio.run_coroutine_threadsafe(self._control_ws.send(msg), self._loop)
            logger.info("Sent delink request to host")


    def send_mouse_move(self, norm_x: float, norm_y: float):
        if self._control_ws and self._loop and self._loop.is_running():
            msg = json.dumps({"type": "mouse_move", "x": norm_x, "y": norm_y})
            asyncio.run_coroutine_threadsafe(self._control_ws.send(msg), self._loop)

    def send_mouse_button(self, button: str, down: bool):
        if self._control_ws and self._loop and self._loop.is_running():
            msg = json.dumps({"type": "mouse_button", "button": button, "down": down})
            asyncio.run_coroutine_threadsafe(self._control_ws.send(msg), self._loop)

    def send_mouse_wheel(self, delta: int):
        if self._control_ws and self._loop and self._loop.is_running():
            msg = json.dumps({"type": "mouse_wheel", "delta": delta})
            asyncio.run_coroutine_threadsafe(self._control_ws.send(msg), self._loop)

    def _run_client(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main_async())

    async def _main_async(self):
        try:
            # Connect control and stream concurrently
            async with websockets.connect(self.control_url) as control_ws, \
                       websockets.connect(self.stream_url, max_size=10 * 1024 * 1024) as stream_ws:
                self._control_ws = control_ws
                self._stream_ws = stream_ws
                self.is_connected = True
                self.connected.emit()
                logger.info("Connected to host stream & control channels")

                # Run frame receiver, control listener, and ping loop concurrently
                await asyncio.gather(
                    self._receive_frames_loop(stream_ws),
                    self._receive_control_loop(control_ws),
                    self._ping_latency_loop(control_ws),
                )
        except Exception as e:
            logger.warning(f"Connection terminated: {e}")
            if self._running:
                self.disconnected.emit(str(e))
        finally:
            self.is_connected = False
            self._running = False

    async def _receive_frames_loop(self, stream_ws):
        fps_count = 0
        fps_timer = time.time()

        while self._running:
            try:
                frame_bytes = await stream_ws.recv()
                if isinstance(frame_bytes, bytes):
                    # Decode directly into QImage from memory buffer
                    img = QImage()
                    if img.loadFromData(frame_bytes, "JPEG"):
                        self.frame_ready.emit(img)
                        fps_count += 1

                if time.time() - fps_timer >= 1.0:
                    self.current_fps = fps_count / (time.time() - fps_timer)
                    self.stats_updated.emit(self.current_fps, self.current_latency_ms)
                    fps_count = 0
                    fps_timer = time.time()

            except websockets.ConnectionClosed:
                break
            except Exception as e:
                logger.debug(f"Frame recv error: {e}")
                break

    async def _receive_control_loop(self, control_ws):
        while self._running:
            try:
                message = await control_ws.recv()
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "activate_monitor":
                    logger.info("Host requested monitor activation!")
                    self.activate_requested.emit()

                elif msg_type == "delink":
                    reason = data.get("reason", "host_delink")
                    logger.info(f"Delink received from host: {reason}")
                    self.delink_received.emit(reason)
                    self.stop()
                    break


                elif msg_type == "delink_ack":
                    logger.info("Delink acknowledged by host")
                    self.delink_received.emit("delink_ack")
                    self.stop()
                    break

                elif msg_type == "pong":
                    sent_time = data.get("time", 0)
                    if sent_time > 0:
                        self.current_latency_ms = (time.time() - sent_time) * 1000.0
                        self.stats_updated.emit(self.current_fps, self.current_latency_ms)

            except websockets.ConnectionClosed:
                break
            except Exception as e:
                logger.debug(f"Control message error: {e}")
                break

    async def _ping_latency_loop(self, control_ws):
        while self._running:
            try:
                msg = json.dumps({"type": "ping", "time": time.time()})
                await control_ws.send(msg)
                await asyncio.sleep(1.0)
            except Exception:
                break

    async def _cleanup(self):
        if self._control_ws:
            try:
                await self._control_ws.close()
            except Exception:
                pass
        if self._stream_ws:
            try:
                await self._stream_ws.close()
            except Exception:
                pass
