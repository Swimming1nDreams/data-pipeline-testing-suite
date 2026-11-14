"""
DataSentinel QA - Standalone Desktop Software Application
Launches DataSentinel QA as a native Windows desktop GUI application using pywebview.
"""

import sys
import os
import threading
import time
import urllib.request
import webview

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = "http://localhost:8082"

def ensure_server_running():
    """Checks if web_server is already running; starts in thread if not."""
    try:
        urllib.request.urlopen(SERVER_URL, timeout=1)
        print("[Desktop App] Background server is already running on port 8082.")
    except Exception:
        print("[Desktop App] Starting local server thread...")
        from web_server import run_server
        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        time.sleep(1)

def main():
    ensure_server_running()
    
    # Create native desktop window
    window = webview.create_window(
        title="DataSentinel QA — Data Pipeline Testing & Profiling Studio",
        url=SERVER_URL,
        width=1380,
        height=880,
        min_size=(1100, 700),
        resizable=True,
        confirm_close=False,
        background_color="#070d19"
    )

    print("=" * 70)
    print("  DataSentinel QA - Desktop Software Launched")
    print("  Native Window Active (Press Alt+F4 to exit)")
    print("=" * 70)
    webview.start()

if __name__ == "__main__":
    main()
