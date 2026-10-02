"""
Host Streamer Server.
Runs high-performance WebSocket endpoints for binary video frame streaming
and JSON control messages (Delink, Handshake, Mouse/Keyboard Events).
Also hosts a built-in HTTP server for browser-based receiver fallback.
"""

import asyncio
import json
import logging
import os
import threading
import time
from typing import Callable, Optional
import websockets
from websockets.server import WebSocketServerProtocol
from PyQt6.QtCore import QObject, pyqtSignal
from core.capture import ScreenCapture, WindowCapture
from core.input_handler import InputHandler

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


class HostStreamer(QObject):
    client_connected = pyqtSignal(object)
    client_disconnected = pyqtSignal(object)
    delink_received = pyqtSignal(str)

    def __init__(
        self,
        port: int = 8765,
        target_fps: int = 60,
        quality: int = 85,
        target_res: tuple[int, int] = (1920, 1080),
        on_client_connected: Optional[Callable] = None,
        on_client_disconnected: Optional[Callable] = None,
        on_delink_received: Optional[Callable] = None,
    ):
        super().__init__()
        self.port = port
        self.target_fps = target_fps
        self.quality = quality
        self.target_res = target_res
        self.on_client_connected = on_client_connected
        self.on_client_disconnected = on_client_disconnected
        self.on_delink_received = on_delink_received

        self._running = False
        self._thread = None
        self._loop = None
        self._server = None

        # Capture source
        self.capture_mode = "display"  # "display" or "window"
        self.display_index = 0
        self.window_hwnd = None
        self.capturer = None

        # Connected clients
        self.stream_clients: set[WebSocketServerProtocol] = set()
        self.control_clients: set[WebSocketServerProtocol] = set()

        # Input passthrough
        self.allow_input_passthrough = True

        # Statistics
        self.current_fps = 0.0
        self.frames_sent = 0
        self.bytes_sent = 0

    def start(self):
        """Start the streamer in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        logger.info(f"HostStreamer starting on port {self.port}")

    def stop(self):
        """Stop the streamer and release capture devices."""
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
        if self.capturer:
            self.capturer.release()
            self.capturer = None
        logger.info("HostStreamer stopped")

    def set_source_display(self, output_idx: int):
        self.capture_mode = "display"
        self.display_index = output_idx
        if self.capturer:
            self.capturer.release()
            self.capturer = None

        width, height = self.target_res
        try:
            from core.virtual_display import VirtualDisplayManager
            displays = VirtualDisplayManager.get_all_displays()
            if 0 <= output_idx < len(displays):
                disp = displays[output_idx]
                width = disp.get("width", width)
                height = disp.get("height", height)
        except Exception as e:
            logger.warning(f"Failed to query display {output_idx} resolution: {e}")

        self.capturer = ScreenCapture(
            output_idx=output_idx,
            target_width=width,
            target_height=height,
            quality=self.quality
        )
        logger.info(f"Streamer source switched to display index {output_idx} ({width}x{height})")

    def set_source_window(self, hwnd: int):
        self.capture_mode = "window"
        self.window_hwnd = hwnd
        if self.capturer:
            self.capturer.release()
            self.capturer = None
        self.capturer = WindowCapture(
            hwnd=hwnd,
            target_width=self.target_res[0],
            target_height=self.target_res[1],
            quality=self.quality
        )
        logger.info(f"Streamer source switched to window {hwnd}")

    def set_quality_and_fps(self, quality: int, fps: int):
        self.quality = quality
        self.target_fps = fps
        if self.capturer:
            self.capturer.quality = quality

    def delink_all(self, reason: str = "host_delink"):
        """Notify all connected laptop receivers to exit fullscreen and disconnect immediately."""
        msg = json.dumps({"type": "delink", "reason": reason})
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast_control(msg), self._loop)
        logger.info(f"Delink signal sent to all receivers: {reason}")

    async def _broadcast_control(self, msg: str):
        for ws in list(self.control_clients):
            try:
                await ws.send(msg)
            except Exception:
                pass

    def _run_server(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._main_async())
        except Exception as e:
            logger.error(f"HostStreamer server loop error: {e}")

    async def _main_async(self):
        # Initialize default capturer
        if not self.capturer:
            self.set_source_display(self.display_index)

        # Start WebSocket server
        # We handle HTTP requests (process_request) to serve the web fallback
        self._server = await websockets.serve(
            self._handle_client,
            "0.0.0.0",
            self.port,
            process_request=self._process_http_request,
            max_size=10 * 1024 * 1024,
            ping_interval=10,
            ping_timeout=5,
        )

        # Launch frame broadcasting loop
        asyncio.create_task(self._capture_broadcast_loop())
        logger.info(f"HostStreamer listening on 0.0.0.0:{self.port}")

        while self._running:
            await asyncio.sleep(0.5)

    async def _process_http_request(self, connection, request):
        """Serves HTTP files for browser receiver if request is not a WebSocket upgrade."""
        upgrade = request.headers.get("Upgrade", "")
        if upgrade and upgrade.lower() == "websocket":
            return None  # Proceed with WebSocket handshake

        from websockets.http11 import Response
        from websockets.datastructures import Headers

        # Handle simple HTTP request
        clean_path = request.path.split("?")[0].strip("/")
        if not clean_path or clean_path in ("index.html", "receiver"):
            file_name = "index.html"
            content_type = "text/html; charset=utf-8"
        elif clean_path.endswith(".js"):
            file_name = os.path.basename(clean_path)
            content_type = "application/javascript"
        elif clean_path.endswith(".css"):
            file_name = os.path.basename(clean_path)
            content_type = "text/css"
        else:
            return Response(404, "Not Found", Headers([("Content-Type", "text/plain")]), b"Not Found")

        file_path = os.path.join(STATIC_DIR, file_name)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                body = f.read()
            headers = Headers([
                ("Content-Type", content_type),
                ("Content-Length", str(len(body))),
                ("Access-Control-Allow-Origin", "*"),
            ])
            return Response(200, "OK", headers, body)
        return Response(404, "Not Found", Headers([("Content-Type", "text/plain")]), b"File Not Found")

    async def _handle_client(self, websocket: WebSocketServerProtocol, *args):
        # Determine path from request or args
        path = getattr(getattr(websocket, "request", None), "path", "")
        if not path and args:
            path = args[0]
        clean_path = path.split("?")[0]
        if clean_path == "/stream":
            self.stream_clients.add(websocket)
            logger.info(f"Stream client connected: {websocket.remote_address}")
            if self.on_client_connected:
                try:
                    self.on_client_connected(websocket.remote_address)
                except Exception as e:
                    logger.debug(f"on_client_connected error: {e}")
            self.client_connected.emit(websocket.remote_address)
            try:
                await websocket.wait_closed()
            except Exception:
                pass
            finally:
                self.stream_clients.discard(websocket)
                logger.info(f"Stream client disconnected: {websocket.remote_address}")
                if self.on_client_disconnected:
                    try:
                        self.on_client_disconnected(websocket.remote_address)
                    except Exception as e:
                        logger.debug(f"on_client_disconnected error: {e}")
                self.client_disconnected.emit(websocket.remote_address)

        elif clean_path == "/control":
            self.control_clients.add(websocket)
            logger.info(f"Control client connected: {websocket.remote_address}")
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_control_message(websocket, data)
                    except Exception as e:
                        logger.error(f"Error handling control message: {e}")
            except Exception:
                pass
            finally:
                self.control_clients.discard(websocket)


    def trigger_link(self):
        """Notify all connected laptop receivers to enter fullscreen monitor mode and receive stream."""
        msg = json.dumps({"type": "activate_monitor"})
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast_control(msg), self._loop)
        logger.info("Sent activate_monitor command to all standby receivers")

    async def _handle_control_message(self, websocket: WebSocketServerProtocol, data: dict):
        msg_type = data.get("type")
        if msg_type == "link_request":
            logger.info("Link requested by client")
            # Automatically start streaming and activate monitor on client
            await websocket.send(json.dumps({"type": "activate_monitor"}))
            if self.on_client_connected:
                try:
                    self.on_client_connected(websocket.remote_address)
                except Exception as e:
                    logger.debug(f"on_client_connected error: {e}")
            self.client_connected.emit(websocket.remote_address)

        elif msg_type == "delink":
            reason = data.get("reason", "client_delink")
            logger.info(f"Delink requested by client: {reason}")
            if self.on_delink_received:
                try:
                    self.on_delink_received(reason)
                except Exception as e:
                    logger.debug(f"on_delink_received error: {e}")
            self.delink_received.emit(reason)
            # Confirm delink
            try:
                await websocket.send(json.dumps({"type": "delink_ack"}))
            except Exception:
                pass
            # Also notify stream clients to close
            for s in list(self.stream_clients):
                try:
                    await s.close()
                except Exception:
                    pass

        elif msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong", "time": data.get("time")}))

        elif msg_type == "mouse_move" and self.allow_input_passthrough:
            norm_x = data.get("x", 0.0)
            norm_y = data.get("y", 0.0)
            InputHandler.send_mouse_move(norm_x, norm_y)

        elif msg_type == "mouse_button" and self.allow_input_passthrough:
            btn = data.get("button", "left")
            down = data.get("down", True)
            InputHandler.send_mouse_button(btn, down)

        elif msg_type == "mouse_wheel" and self.allow_input_passthrough:
            delta = data.get("delta", 0)
            InputHandler.send_mouse_wheel(delta)

    async def _capture_broadcast_loop(self):

        last_time = time.time()
        fps_count = 0
        fps_timer = time.time()

        while self._running:
            target_interval = 1.0 / max(1, self.target_fps)
            loop_start = time.time()

            if self.stream_clients and self.capturer:
                # Capture frame
                jpeg_bytes = self.capturer.capture_compressed_jpeg()
                if jpeg_bytes:
                    fps_count += 1
                    self.frames_sent += 1
                    self.bytes_sent += len(jpeg_bytes)

                    # Send to all stream clients concurrently
                    coros = []
                    for client in list(self.stream_clients):
                        # Don't pile up frames if client connection is slow
                        coros.append(client.send(jpeg_bytes))
                    if coros:
                        await asyncio.gather(*coros, return_exceptions=True)

            # Update FPS calculation
            if time.time() - fps_timer >= 1.0:
                self.current_fps = fps_count / (time.time() - fps_timer)
                fps_count = 0
                fps_timer = time.time()

            # Maintain frame rate timing
            elapsed = time.time() - loop_start
            sleep_needed = target_interval - elapsed
            if sleep_needed > 0:
                await asyncio.sleep(sleep_needed)
            else:
                await asyncio.sleep(0.001)

    async def _shutdown(self):
        # Close all clients
        for c in list(self.control_clients):
            try:
                await c.close()
            except Exception:
                pass
        for s in list(self.stream_clients):
            try:
                await s.close()
            except Exception:
                pass
        if self._server:
            self._server.close()
            await self._server.wait_closed()
