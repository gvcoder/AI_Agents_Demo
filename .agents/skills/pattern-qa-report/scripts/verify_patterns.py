#!/usr/bin/env python3
"""
Automated QA & verification script for AI Agent Design Patterns Playground.
Checks backend imports, registered pattern routes, frontend build, and outputs JSON summary.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BACKEND_PYTHON = ROOT / ".venv" / "bin" / "python"
FRONTEND_DIR = ROOT / "frontend"


def check_backend_routes():
    python_bin = str(BACKEND_PYTHON) if BACKEND_PYTHON.exists() else sys.executable
    cmd = [
        python_bin,
        "-c",
        (
            "import json; from backend.app.main import app; "
            "paths = sorted(app.openapi()['paths'].keys()); "
            "print(json.dumps(paths))"
        ),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        return {"ok": False, "routes": [], "error": proc.stderr.strip()}
    try:
        routes = json.loads(proc.stdout.strip().splitlines()[-1])
        return {"ok": True, "routes": routes, "error": None}
    except Exception as exc:
        return {"ok": False, "routes": [], "error": str(exc)}


def check_frontend_build():
    proc = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
    )
    return {
        "ok": proc.returncode == 0,
        "error": None if proc.returncode == 0 else proc.stderr.strip() or proc.stdout.strip(),
    }


def check_env_providers():
    env_file = ROOT / ".env"
    providers = {"gemini": False, "openai": False, "anthropic": False}
    if not env_file.exists():
        return {"env_exists": False, "providers": providers}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if k == "GEMINI_API_KEY":
            providers["gemini"] = bool(v)
        elif k == "OPENAI_API_KEY":
            providers["openai"] = bool(v)
        elif k == "ANTHROPIC_API_KEY":
            providers["anthropic"] = bool(v)
    return {"env_exists": True, "providers": providers}


def main():
    report = {
        "backend": check_backend_routes(),
        "frontend_build": check_frontend_build(),
        "env": check_env_providers(),
    }
    print(json.dumps(report, indent=2))
    if not (report["backend"]["ok"] and report["frontend_build"]["ok"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
