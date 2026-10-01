(function() {
    const loc = window.location;
    const wsProto = loc.protocol === "https:" ? "wss:" : "ws:";
    const streamUrl = `${wsProto}//${loc.host}/stream`;
    const controlUrl = `${wsProto}//${loc.host}/control`;

    const canvas = document.getElementById("display-canvas");
    const ctx = canvas.getContext("2d");
    const overlay = document.getElementById("overlay");
    const overlayMsg = document.getElementById("overlay-msg");
    const spinner = document.getElementById("spinner");
    const retryBtn = document.getElementById("retry-btn");
    const fullscreenBtn = document.getElementById("fullscreen-btn");
    const delinkBtn = document.getElementById("delink-btn");
    const fpsStat = document.getElementById("fps-stat");
    const pingStat = document.getElementById("ping-stat");
    const hud = document.getElementById("hud");

    let streamWs = null;
    let controlWs = null;
    let frameCount = 0;
    let lastFpsTime = performance.now();
    let img = new Image();

    function connect() {
        overlay.style.display = "flex";
        spinner.style.display = "block";
        retryBtn.style.display = "none";
        overlayMsg.textContent = "Connecting to PC screen...";

        controlWs = new WebSocket(controlUrl);
        controlWs.onopen = () => {
            console.log("Control connected");
            startPing();
        };

        controlWs.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === "delink" || msg.type === "delink_ack") {
                    overlayMsg.textContent = "Disconnected (Delinked by host or client)";
                    overlay.style.display = "flex";
                    spinner.style.display = "none";
                    retryBtn.style.display = "inline-block";
                    disconnectAll();
                } else if (msg.type === "pong") {
                    const rtt = Math.round(performance.now() - msg.time);
                    pingStat.textContent = `${rtt} ms`;
                }
            } catch (e) {}
        };

        streamWs = new WebSocket(streamUrl);
        streamWs.binaryType = "blob";

        streamWs.onopen = () => {
            console.log("Stream connected");
            overlay.style.display = "none";
        };

        streamWs.onmessage = (event) => {
            if (event.data instanceof Blob) {
                const url = URL.createObjectURL(event.data);
                img.onload = () => {
                    if (canvas.width !== img.width || canvas.height !== img.height) {
                        canvas.width = img.width;
                        canvas.height = img.height;
                    }
                    ctx.drawImage(img, 0, 0);
                    URL.revokeObjectURL(url);
                    frameCount++;
                };
                img.src = url;
            }
        };

        streamWs.onclose = () => {
            overlayMsg.textContent = "Screen stream closed.";
            overlay.style.display = "flex";
            spinner.style.display = "none";
            retryBtn.style.display = "inline-block";
        };

        streamWs.onerror = () => {
            overlayMsg.textContent = "Connection error.";
            overlay.style.display = "flex";
            spinner.style.display = "none";
            retryBtn.style.display = "inline-block";
        };
    }

    function disconnectAll() {
        if (streamWs) { streamWs.close(); streamWs = null; }
        if (controlWs) { controlWs.close(); controlWs = null; }
    }

    function startPing() {
        setInterval(() => {
            if (controlWs && controlWs.readyState === WebSocket.OPEN) {
                controlWs.send(JSON.stringify({ type: "ping", time: performance.now() }));
            }
        }, 1000);
    }

    // FPS loop
    setInterval(() => {
        const now = performance.now();
        const fps = Math.round((frameCount * 1000) / (now - lastFpsTime));
        fpsStat.textContent = `${fps} FPS`;
        frameCount = 0;
        lastFpsTime = now;
    }, 1000);

    // Fullscreen toggle
    fullscreenBtn.onclick = () => {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(() => {});
        } else {
            document.exitFullscreen().catch(() => {});
        }
    };

    // Delink button
    delinkBtn.onclick = () => {
        if (controlWs && controlWs.readyState === WebSocket.OPEN) {
            controlWs.send(JSON.stringify({ type: "delink", reason: "web_client_exit" }));
        }
        disconnectAll();
        overlayMsg.textContent = "Delinked from PC.";
        overlay.style.display = "flex";
        spinner.style.display = "none";
        retryBtn.style.display = "inline-block";
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => {});
        }
    };

    retryBtn.onclick = () => {
        connect();
    };

    // Mouse movement passthrough
    canvas.addEventListener("mousemove", (e) => {
        if (controlWs && controlWs.readyState === WebSocket.OPEN) {
            const rect = canvas.getBoundingClientRect();
            const normX = (e.clientX - rect.left) / rect.width;
            const normY = (e.clientY - rect.top) / rect.height;
            controlWs.send(JSON.stringify({ type: "mouse_move", x: normX, y: normY }));
        }
    });

    connect();
})();
