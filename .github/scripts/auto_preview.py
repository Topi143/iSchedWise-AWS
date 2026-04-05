#!/usr/bin/env python3
"""
Auto Preview

Manages (start/stop/status) a local preview process.

Usage:
    python .github/scripts/auto_preview.py start [port]
    python .github/scripts/auto_preview.py stop
    python .github/scripts/auto_preview.py status
"""

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

STATE_DIR = Path(".github")
PID_FILE = STATE_DIR / "preview.pid"
LOG_FILE = STATE_DIR / "preview.log"
URL_FILE = STATE_DIR / "preview.url"


def get_project_root() -> Path:
    return Path(".").resolve()


def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_start_command(root: Path):
    # IntellEvalPro/Flask first
    if (root / "app.py").exists():
        return [sys.executable, "app.py"], "http://localhost:5000"

    # Node fallback for other projects
    pkg_file = root / "package.json"
    if pkg_file.exists():
        with open(pkg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        scripts = data.get("scripts", {})
        if "dev" in scripts:
            return ["npm", "run", "dev"], "http://localhost:3000"
        if "start" in scripts:
            return ["npm", "start"], "http://localhost:3000"

    return None, None


def start_server(port: int = 3000):
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
            if is_running(pid):
                print(f"WARN: Preview already running (PID: {pid})")
                return
        except Exception:
            pass

    root = get_project_root()
    cmd, url = get_start_command(root)
    if not cmd:
        print("ERROR: No start command found (expected app.py or package.json scripts).")
        sys.exit(1)

    env = os.environ.copy()
    env["PORT"] = str(port)

    print(f"Starting preview with command: {' '.join(cmd)}")
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        process = subprocess.Popen(
            cmd,
            cwd=str(root),
            stdout=log,
            stderr=log,
            env=env,
            shell=False,
        )

    PID_FILE.write_text(str(process.pid), encoding="utf-8")
    if url:
        URL_FILE.write_text(url, encoding="utf-8")

    print(f"OK: Preview started (PID: {process.pid})")
    print(f"Logs: {LOG_FILE}")
    if url:
        print(f"URL: {url}")


def stop_server():
    if not PID_FILE.exists():
        print("INFO: No preview server found.")
        return

    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        if is_running(pid):
            if sys.platform == "win32":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(pid)])
            else:
                os.kill(pid, signal.SIGTERM)
            print(f"OK: Preview stopped (PID: {pid})")
        else:
            print("INFO: Process was not running.")
    except Exception as exc:
        print(f"ERROR: Failed to stop preview: {exc}")
    finally:
        for file_path in (PID_FILE, URL_FILE):
            if file_path.exists():
                file_path.unlink()


def status_server():
    print("\n=== Preview Status ===")
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
            if is_running(pid):
                url = URL_FILE.read_text(encoding="utf-8").strip() if URL_FILE.exists() else "Unknown"
                print("Status: Running")
                print(f"PID: {pid}")
                print(f"URL: {url}")
                print(f"Logs: {LOG_FILE}")
                print("======================\n")
                return
        except Exception:
            pass

    print("Status: Stopped")
    print("======================\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("port", nargs="?", default="3000")
    args = parser.parse_args()

    if args.action == "start":
        start_server(int(args.port))
    elif args.action == "stop":
        stop_server()
    elif args.action == "status":
        status_server()


if __name__ == "__main__":
    main()

