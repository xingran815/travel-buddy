"""Whisper model setup endpoint: status check and streaming download."""

import json
import os
import threading
import urllib.request
from pathlib import Path

import whisper
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

_MODEL_NAME = "small"


def _model_url() -> str:
    return whisper._MODELS[_MODEL_NAME]


def _cached_model_path() -> Path | None:
    """Return the cached model file path if it already exists."""
    cache_dir = Path.home() / ".cache" / "whisper"
    filename = os.path.basename(_model_url())
    path = cache_dir / filename
    return path if path.exists() else None


@router.get("/setup/whisper-status")
def whisper_status() -> dict:
    """Return whether the Whisper model is already cached locally."""
    path = _cached_model_path()
    return {"ready": path is not None, "model": _MODEL_NAME, "path": str(path) if path else None}


@router.get("/setup/whisper-download")
async def whisper_download():
    """SSE stream that downloads the Whisper model with real byte-level progress.

    Events: ``{"step": "checking"|"downloading"|"done"|"error", "progress": 0.0-1.0}``
    """
    async def generate():
        yield {"data": json.dumps({"step": "checking", "progress": 0.0})}

        if _cached_model_path():
            yield {"data": json.dumps({"step": "done", "progress": 1.0})}
            return

        url = _model_url()
        cache_dir = Path.home() / ".cache" / "whisper"
        cache_dir.mkdir(parents=True, exist_ok=True)
        dest = cache_dir / os.path.basename(url)
        tmp = dest.with_suffix(".part")

        state: dict = {"downloaded": 0, "total": 0, "done": False, "error": None}

        def _download():
            try:
                req = urllib.request.urlopen(url)
                state["total"] = int(req.headers.get("Content-Length", 0))
                with open(tmp, "wb") as f:
                    while True:
                        chunk = req.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        state["downloaded"] += len(chunk)
                tmp.rename(dest)
            except Exception as exc:
                state["error"] = str(exc)
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
            finally:
                state["done"] = True

        thread = threading.Thread(target=_download, daemon=True)
        thread.start()

        import asyncio
        yield {"data": json.dumps({"step": "downloading", "progress": 0.01})}

        while not state["done"]:
            await asyncio.sleep(0.3)
            total = state["total"]
            downloaded = state["downloaded"]
            if total > 0:
                progress = min(0.99, downloaded / total)
                yield {"data": json.dumps({"step": "downloading", "progress": round(progress, 3)})}

        if state["error"]:
            yield {"data": json.dumps({"step": "error", "progress": 0.0, "message": state["error"]})}
        else:
            yield {"data": json.dumps({"step": "done", "progress": 1.0})}

    return EventSourceResponse(generate())
