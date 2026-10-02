# MonitorLink — Project Roadmap & Milestone Map

This document tracks the past, current, and upcoming architectural milestones for MonitorLink.

---

## 🏁 Phase 1: Core Foundation & Stability (Current)

### ✅ v1.0.0 — Initial Release
- [x] DirectX 11 DXGI Desktop Duplication pipeline (60 FPS real-time capture).
- [x] Dual-endpoint WebSocket streaming (`/stream` binary JPEG frames, `/control` bi-directional JSON).
- [x] Dedicated Laptop Standby Mode using Win32 `SetThreadExecutionState`.
- [x] Edge-to-edge hardware-accelerated canvas with auto-hiding cursor.
- [x] Zero-config UDP network beacon auto-discovery on local LAN and point-to-point connections.
- [x] Bundled Microsoft IddCx Virtual Display Driver for genuine secondary displays.

### ✅ v1.1.0 — Display Topology, True Colors & Pacing Fixes
- [x] **Windows Display Settings Alignment**: Enumerated monitor layout directly via `EnumDisplayMonitors` desktop topology coordinates. Display 1, 2, and 3 now match Windows Display Settings 1:1.
- [x] **Color Distortion & Inversion Resolution**: Enforced native BGR capture across DXGI and compression pipelines, eliminating color flipping on mouse motion.
- [x] **Frame Pacing & Stutter Elimination**: Implemented smart keepalive frame caching on static screens, stopping slow GDI fallback oscillations.
- [x] **Dynamic Display Resolution**: Preserved native resolutions (e.g. 1440p, 1080p) without forced downscaling.
- [x] **Thread-Safe Event Delivery**: Converted streamer and discovery networking into asynchronous Qt signal queues to prevent crashes on client delink.
- [x] **Portable Standalone Launchers**: Updated `run_pc.bat` and `run_laptop.bat` to detect portable executables out-of-the-box.

---

## 🚀 Phase 2: Enhanced Multimedia & Performance (Upcoming)

### 🎯 v1.2.0 — Audio Passthrough & Hardware Codecs
- [ ] **WASAPI Audio Loopback**: Low-latency desktop audio capture streamed to laptop speakers alongside the video feed.
- [ ] **Hardware Video Encoding (H.264 / H.265 / AV1)**:
  - NVIDIA NVENC, AMD AMF, and Intel QuickSync acceleration.
  - Up to 50% network bandwidth reduction with sub-10ms encode overhead.
- [ ] **Dynamic Bitrate Control**: Automatic quality adjustment based on real-time ping/pong round-trip latency.

---

## 🌐 Phase 3: Input & Cross-Platform Expansion

### 🎯 v1.3.0 — Stylus, Touchscreen & Multi-Platform
- [ ] **Touchscreen & Stylus Passthrough**: Forward Windows Ink, touch gestures, and pen pressure levels from laptops/tablets back to host PC.
- [ ] **macOS / Linux Receivers**: Cross-platform receiver app built on PyQt6 / WebRTC to turn MacBooks and Linux laptops into second screens.
- [ ] **Encrypted LAN Streaming**: Optional TLS/WSS encryption and PIN code pairing for shared Wi-Fi networks.
