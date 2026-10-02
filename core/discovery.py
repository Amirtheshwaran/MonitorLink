"""
Local Network Device Discovery.
Uses UDP beacon broadcast to automatically detect PC Host and Laptop Receivers
on the same Wi-Fi network, direct Ethernet cable, or USB connection.
"""

import socket
import json
import time
import threading
import logging
import ipaddress
import psutil

logger = logging.getLogger(__name__)

DISCOVERY_PORT = 8766
BEACON_INTERVAL = 1.0
DEVICE_TIMEOUT = 3.5

HOST_ROLES = {"pc", "host", "sender"}
CLIENT_ROLES = {"laptop", "receiver", "client"}


def is_opposite_role(r1: str, r2: str) -> bool:
    """Return True if r1 and r2 represent complementary host/receiver roles."""
    return (r1 in HOST_ROLES and r2 in CLIENT_ROLES) or (r1 in CLIENT_ROLES and r2 in HOST_ROLES)


def get_local_ip_addresses() -> list[dict]:
    """Get all non-loopback IPv4 addresses with their interface names, types, and broadcast addresses."""
    results = []
    try:
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    is_wired = any(k in iface.lower() for k in ["ethernet", "lan", "local area", "usb"])
                    bcast = None
                    if addr.netmask:
                        try:
                            net = ipaddress.IPv4Network(f"{addr.address}/{addr.netmask}", strict=False)
                            bcast = str(net.broadcast_address)
                        except Exception:
                            pass
                    results.append({
                        "iface": iface,
                        "ip": addr.address,
                        "bcast": bcast,
                        "type": "Wired (Ethernet/USB)" if is_wired else "Wi-Fi (Wireless)"
                    })
    except Exception as e:
        logger.error(f"Error enumerating local IP addresses: {e}")

    if not results:
        results.append({"iface": "Default", "ip": "127.0.0.1", "bcast": "255.255.255.255", "type": "Loopback"})
    return results


class DiscoveryService:
    def __init__(self, role: str, service_port: int, on_device_found=None, on_device_lost=None):
        self.role = role  # "host" or "receiver"
        self.service_port = service_port
        self.hostname = socket.gethostname()
        self.on_device_found = on_device_found
        self.on_device_lost = on_device_lost
        
        self.discovered_devices = {}  # key: f"{ip}:{port}" -> device_info
        self._running = False
        self._broadcast_thread = None
        self._listener_thread = None
        self._cleanup_thread = None

    def start(self):
        self._running = True
        
        # Start broadcaster
        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._broadcast_thread.start()
        
        # Start listener
        self._listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self._listener_thread.start()

        # Start cleanup
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info(f"Discovery service started as role='{self.role}' on port {DISCOVERY_PORT}")

    def stop(self):
        self._running = False

    def _broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.5)

        while self._running:
            ips = get_local_ip_addresses()
            for item in ips:
                ip = item["ip"]
                msg = {
                    "type": "beacon",
                    "role": self.role,
                    "hostname": self.hostname,
                    "ip": ip,
                    "port": self.service_port,
                    "network_type": item["type"],
                    "timestamp": time.time()
                }
                payload = json.dumps(msg).encode("utf-8")
                try:
                    sock.sendto(payload, ("<broadcast>", DISCOVERY_PORT))
                    if item.get("bcast"):
                        sock.sendto(payload, (item["bcast"], DISCOVERY_PORT))
                    # Also try naive /24 broadcast fallback
                    parts = ip.split(".")
                    if len(parts) == 4:
                        parts[3] = "255"
                        sock.sendto(payload, (".".join(parts), DISCOVERY_PORT))
                except Exception:
                    pass
            time.sleep(BEACON_INTERVAL)
        sock.close()

    def _listener_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", DISCOVERY_PORT))
        except Exception as e:
            logger.error(f"Failed to bind discovery listener: {e}")
            return

        sock.settimeout(1.0)
        while self._running:
            try:
                data, addr = sock.recvfrom(2048)
                msg = json.loads(data.decode("utf-8"))
                if msg.get("type") == "beacon" and is_opposite_role(self.role, msg.get("role", "")):
                    key = f"{msg.get('ip')}:{msg.get('port')}"
                    msg["last_seen"] = time.time()
                    msg["remote_addr"] = addr[0]

                    is_new = key not in self.discovered_devices
                    self.discovered_devices[key] = msg
                    if is_new and self.on_device_found:
                        self.on_device_found(msg)
            except socket.timeout:
                continue
            except Exception as e:
                logger.debug(f"Discovery listener error: {e}")
        sock.close()

    def _cleanup_loop(self):
        while self._running:
            now = time.time()
            to_remove = []
            for key, dev in list(self.discovered_devices.items()):
                if now - dev.get("last_seen", 0) > DEVICE_TIMEOUT:
                    to_remove.append(key)

            for key in to_remove:
                lost_dev = self.discovered_devices.pop(key, None)
                if lost_dev and self.on_device_lost:
                    self.on_device_lost(lost_dev)
            time.sleep(1.0)

    def get_devices(self) -> list[dict]:
        return list(self.discovered_devices.values())
