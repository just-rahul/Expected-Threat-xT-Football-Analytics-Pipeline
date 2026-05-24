"""
Single-command launcher for Hybrid Sentinel.
Builds frontend if needed, then starts the backend server.

Usage:
    python start.py          # Default port 8000
    python start.py --port 3000
"""

import os
import subprocess
import sys
import argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
BACKEND = os.path.join(ROOT, "backend")
DIST = os.path.join(FRONTEND, "dist")


def build_frontend():
    """Build the React frontend if dist/ doesn't exist."""
    if os.path.isdir(DIST):
        print("✓ Frontend build found")
        return

    print("⚙ Building frontend...")
    if not os.path.isdir(os.path.join(FRONTEND, "node_modules")):
        subprocess.run(["npm", "install"], cwd=FRONTEND, check=True, shell=True)
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=True, shell=True)
    print("✓ Frontend built successfully")


def start_server(port: int):
    """Start the FastAPI server."""
    print(f"\n🚀 Starting Hybrid Sentinel on http://localhost:{port}")
    print(f"   Upload CSV at the homepage to begin analysis\n")
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", str(port), "--reload"],
        cwd=BACKEND,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hybrid Sentinel Launcher")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args = parser.parse_args()

    build_frontend()
    start_server(args.port)
