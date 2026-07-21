"""
KNWLDGBox — Desktop Application Launcher

Opens the application in a native desktop window using PyWebView.
The FastAPI backend runs in a background thread and serves both
the API and the pre-built Vue frontend on a single port.

Usage:
    python launcher.py              # Default port 8000
    python launcher.py --port 9000  # Custom port
    python launcher.py --dev        # Dev mode (no window, just backend)
"""

import argparse
import os
import sys
import threading
import time
import socket

import uvicorn

from config import APP_DIR, DATA_DIR, TOOL_DIRS


def _setup_environment():
    """Make bundled CLI tools, ffmpeg and browsers discoverable by the backend."""
    # Bundled CLI tools (sherlock, maigret, yt-dlp, holehe) and ffmpeg.
    # Services invoke these by bare name via subprocess → they must be on PATH.
    extra_paths = [str(d) for d in TOOL_DIRS]

    ffmpeg_dir = APP_DIR.parent / 'tools' / 'ffmpeg'
    if ffmpeg_dir.is_dir():
        extra_paths.append(str(ffmpeg_dir))

    if extra_paths:
        os.environ["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + os.environ.get("PATH", "")

    # Use the Playwright browsers bundled by the Windows installer, if present.
    # (Default per-user location in %LOCALAPPDATA% is used otherwise.)
    bundled_browsers = APP_DIR.parent / 'playwright-browsers'
    if bundled_browsers.is_dir() and 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ:
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(bundled_browsers)


def _redirect_logs():
    """
    Under pythonw.exe (Windows install) sys.stdout/sys.stderr are None, which
    would silently swallow every uvicorn/backend error. Redirect to a log file.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_dir = DATA_DIR / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(log_dir / 'knwldgbox.log', 'a', encoding='utf-8', errors='replace')
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file


def is_port_available(port: int) -> bool:
    """Check if a TCP port is free."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def find_free_port(start: int = 8000, end: int = 8100) -> int:
    """Find the first available port in the given range."""
    for port in range(start, end):
        if is_port_available(port):
            return port
    raise RuntimeError(f"No free port found in range {start}-{end}")


def start_backend(port: int):
    """Run the FastAPI/Uvicorn server in the current thread."""
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )


def wait_for_backend(port: int, timeout: float = 15.0):
    """Block until the backend is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_port_available(port):
            return True
        time.sleep(0.2)
    return False


def main():
    _redirect_logs()
    _setup_environment()

    parser = argparse.ArgumentParser(description="KNWLDGBox Desktop Launcher")
    parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--dev", action="store_true", help="Dev mode: run backend only, no window")
    args = parser.parse_args()

    port = args.port if is_port_available(args.port) else find_free_port(args.port + 1)
    url = f"http://127.0.0.1:{port}"

    if args.dev:
        # Dev mode: just run the backend, no native window
        print(f"🚀 KNWLDGBox (dev) → {url}")
        start_backend(port)
        return

    # Production mode: backend in background thread, frontend in native window
    print(f"🚀 Starting KNWLDGBox on {url}")

    # Start backend in a daemon thread
    backend_thread = threading.Thread(target=start_backend, args=(port,), daemon=True)
    backend_thread.start()

    # Wait for the backend to be ready
    if not wait_for_backend(port):
        print("❌ Backend failed to start within 15 seconds.", file=sys.stderr)
        sys.exit(1)

    # Open native window
    import webview  # Import here so pywebview is only required in desktop mode

    window = webview.create_window(
        title="KNWLDGBox",
        url=url,
        width=1400,
        height=900,
        min_size=(1024, 600),
        text_select=True,
    )
    webview.start(debug=False)

    # When the window is closed, the daemon thread dies automatically
    print("👋 KNWLDGBox closed.")


if __name__ == "__main__":
    main()
