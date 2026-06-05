"""Summarize endpoint: streams YouTube download → transcribe → translate → summarize.

Progress is pushed to the client as server-sent events (one per pipeline stage),
ending with the full summary payload. A lock serializes transcription so
concurrent requests don't contend for the (memory-heavy) Whisper model.
"""

import asyncio
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.llm.client import summarize_text, translate_text
from app.server.schemas import SummarizeRequest
from app.youtube.downloader import cleanup, download_audio, get_video_title
from app.youtube.transcriber import transcribe

router = APIRouter()

_transcribe_lock = asyncio.Lock()


def _sse_data(step: str, progress: float, data: dict | None = None) -> str:
    """Serialize one ``{step, progress, data?}`` SSE payload as a JSON string."""
    payload = {"step": step, "progress": progress}
    if data is not None:
        payload["data"] = data
    return json.dumps(payload)


@router.post("/summarize")
async def summarize_video(req: SummarizeRequest):
    """Stream the summarization pipeline for a video URL as SSE progress events."""
    async def generate():
        video_id = None
        try:
            yield {"data": _sse_data("downloading", 0.0)}
            audio_path, video_id = await asyncio.to_thread(download_audio, req.url)
            title = await asyncio.to_thread(get_video_title, req.url)
            yield {"data": _sse_data(
                "download_done", 0.25, {"title": title, "video_id": video_id},
            )}

            yield {"data": _sse_data("transcribing", 0.25)}
            async with _transcribe_lock:
                result = await asyncio.to_thread(transcribe, audio_path)
            source_lang = result["language"]
            yield {"data": _sse_data(
                "transcribe_done", 0.50, {"language": source_lang},
            )}

            translation = None
            if source_lang != req.lang:
                yield {"data": _sse_data("translating", 0.50)}
                translation = await asyncio.to_thread(
                    translate_text, result["text"], req.lang, source_lang,
                )
                yield {"data": _sse_data("translate_done", 0.75)}
                text_for_summary = translation
            else:
                yield {"data": _sse_data(
                    "translate_done", 0.75, {"skipped": True},
                )}
                text_for_summary = result["text"]

            yield {"data": _sse_data("summarizing", 0.75)}
            summary = await asyncio.to_thread(summarize_text, text_for_summary, req.lang)

            await asyncio.to_thread(cleanup, video_id)

            yield {"data": _sse_data("summarize_done", 1.0, {
                "title": title,
                "source_language": source_lang,
                "translation": translation,
                "summary": summary,
                "video_id": video_id,
            })}

        except Exception as exc:
            if video_id:
                try:
                    await asyncio.to_thread(cleanup, video_id)
                except Exception:
                    pass
            yield {"data": _sse_data("error", 0.0, {"message": str(exc)})}

    return EventSourceResponse(generate())
