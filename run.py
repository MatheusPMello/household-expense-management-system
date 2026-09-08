#!/usr/bin/env python3
"""
HomeLedger - Universal Automation & Lifecycle Script
Cross-platform tool to setup, start, test, and manage the HomeLedger stack.

Usage:
    python run.py setup    # Set up virtual environment, dependencies, and database migrations
    python run.py start    # Run both backend and frontend concurrently in development mode
    python run.py test     # Run the full automated backend test suite and frontend build check
    python run.py docker   # Start the production multi-container Docker stack
"""

import os
import sys
import subprocess
import shutil
import time
import signal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

IS_WINDOWS = sys.platform == "win32"
VENV_DIR = BACKEND_DIR / "venv"
VENV_PYTHON = (
    VENV_DIR / "Scripts" / "python.exe"
    if IS_WINDOWS
    else VENV_DIR / "bin" / "python"
)
VENV_PIP = (
    VENV_DIR / "Scripts" / "pip.exe"
    if IS_WINDOWS
    else VENV_DIR / "bin" / "pip"
)
VENV_ALEMBIC = (
    VENV_DIR / "Scripts" / "alembic.exe"
    if IS_WINDOWS
    else VENV_DIR / "bin" / "alembic"
)
VENV_PYTEST = (
    VENV_DIR / "Scripts" / "pytest.exe"
    if IS_WINDOWS
    else VENV_DIR / "bin" / "pytest"
)
VENV_UVICORN = (
    VENV_DIR / "Scripts" / "uvicorn.exe"
    if IS_WINDOWS
    else VENV_DIR / "bin" / "uvicorn"
)


def log(title: str, message: str = ""):
    print(f"\n\033[1;32m[HomeLedger]\033[0m \033[1m{title}\033[0m {message}")


def log_err(message: str):
    print(f"\033[1;31m[Error]\033[0m {message}", file=sys.stderr)


def check_command(cmd: str, name: str):
    if not shutil.which(cmd):
        log_err(f"'{cmd}' was not found in your system PATH. Please install {name} first.")
        sys.exit(1)


def cmd_setup():
    log("Running automated project setup...")

    # 1. Verify Prerequisites
    check_command("node", "Node.js (v18+)")
    check_command("npm", "npm")

    # 2. Setup Backend Virtualenv
    if not VENV_DIR.exists():
        log("Creating Python virtual environment in backend/venv...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    else:
        log("Python virtual environment already exists.")

    # 3. Install Backend Dependencies
    log("Installing backend dependencies...")
    subprocess.run(
        [str(VENV_PIP), "install", "--upgrade", "pip"],
        check=True,
    )
    subprocess.run(
        [str(VENV_PIP), "install", "-r", str(BACKEND_DIR / "requirements.txt")],
        check=True,
    )

    # 4. Run Alembic Database Migrations
    log("Applying database migrations with Alembic...")
    subprocess.run(
        [str(VENV_ALEMBIC), "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        check=True,
    )

    # 5. Setup Frontend Dependencies
    log("Installing frontend dependencies with npm...")
    subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), shell=IS_WINDOWS, check=True)

    log("Setup completed successfully!", "You can now run: python run.py start")


def cmd_test():
    log("Running automated verification suite...")

    # 1. Backend Pytest
    log("Executing backend pytest suite...")
    ret_backend = subprocess.run(
        [str(VENV_PYTEST), "-v"],
        cwd=str(BACKEND_DIR),
    )
    if ret_backend.returncode != 0:
        log_err("Backend tests failed.")
        sys.exit(ret_backend.returncode)

    # 2. Frontend Build / Typecheck
    log("Checking frontend type compilation and Vite build...")
    ret_frontend = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(FRONTEND_DIR),
        shell=IS_WINDOWS,
    )
    if ret_frontend.returncode != 0:
        log_err("Frontend build check failed.")
        sys.exit(ret_frontend.returncode)

    log("All backend tests and frontend compilation checks passed!")


def cmd_start():
    if not VENV_PYTHON.exists() or not (FRONTEND_DIR / "node_modules").exists():
        log("Dependencies not detected. Running initial setup first...")
        cmd_setup()

    log("Starting HomeLedger Development Stack...")
    log("Backend:", "http://localhost:8000  (API Docs: http://localhost:8000/docs)")
    log("Frontend:", "http://localhost:5173")
    print("\nPress Ctrl+C to terminate both servers.\n")

    processes = []
    try:
        # Start Backend Server
        backend_cmd = [
            str(VENV_UVICORN),
            "app.main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
        p_backend = subprocess.Popen(backend_cmd, cwd=str(BACKEND_DIR))
        processes.append(p_backend)

        time.sleep(1)

        # Start Frontend Dev Server
        p_frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR),
            shell=IS_WINDOWS,
        )
        processes.append(p_frontend)

        # Keep parent script running and monitor processes
        while True:
            for p in processes:
                poll = p.poll()
                if poll is not None:
                    raise KeyboardInterrupt
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\033[1;33m[HomeLedger]\033[0m Shutting down servers gracefully...")
        for p in processes:
            try:
                if IS_WINDOWS:
                    # Windows process termination
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
                    p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        print("\033[1;32m[HomeLedger]\033[0m Servers stopped.")


def cmd_docker():
    check_command("docker", "Docker")
    log("Launching production containers via Docker Compose...")
    subprocess.run(["docker", "compose", "up", "--build"], cwd=str(ROOT_DIR), check=True)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1].lower()
    if command == "setup":
        cmd_setup()
    elif command in ("start", "dev", "run"):
        cmd_start()
    elif command in ("test", "verify"):
        cmd_test()
    elif command == "docker":
        cmd_docker()
    else:
        print(f"Unknown command: '{command}'")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
