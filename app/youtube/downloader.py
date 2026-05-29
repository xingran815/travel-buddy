"""YouTube audio extraction via ``yt-dlp`` for the summarize pipeline."""

import os
import glob
import yt_dlp


def download_audio(url: str, output_dir: str = "downloads") -> tuple[str, str]:
    """Download a video's audio as WAV and return ``(filepath, video_id)``.

    Picks the smallest available audio stream (transcription doesn't need
    fidelity) and falls back to the ``.mp3`` path if WAV extraction didn't run."""
    os.makedirs(output_dir, exist_ok=True)
    out_template = os.path.join(output_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "worstaudio/worst",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
        }],
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info["id"]
        filepath = os.path.join(output_dir, f"{video_id}.wav")
        if not os.path.exists(filepath):
            filepath = os.path.join(output_dir, f"{video_id}.mp3")
        return filepath, video_id


def cleanup(video_id: str, output_dir: str = "downloads"):
    """Delete all downloaded files for ``video_id`` from ``output_dir``."""
    for f in glob.glob(os.path.join(output_dir, f"{video_id}.*")):
        os.remove(f)


def get_video_title(url: str) -> str:
    """Fetch a video's title without downloading; ``"Unknown"`` if unavailable."""
    ydl_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("title", "Unknown")
