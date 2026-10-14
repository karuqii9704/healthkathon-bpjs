"""PayRay API: entrypoint FastAPI."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

VERSION = "2.0.0-dev"
ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"


def _git_sha() -> str:
    sha = os.environ.get("GIT_SHA") or os.environ.get("RENDER_GIT_COMMIT")
    if sha:
        return sha[:12]
    try:
        out = subprocess.run(  # nosec B603 B607
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=2, check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


GIT_SHA = _git_sha()

app = FastAPI(title="PayRay", version=VERSION, docs_url=None, redoc_url=None)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION, "git_sha": GIT_SHA}


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
