"""Speech-to-text transcription via OpenAI Whisper."""

import torch
import whisper


def transcribe(audio_path: str, model_name: str = "small") -> dict:
    """Transcribe an audio file, returning ``{"text", "language"}``.

    Uses FP16 only when a CUDA GPU is available; the detected source language
    drives whether the summarize pipeline translates before summarizing."""
    fp16 = torch.cuda.is_available()
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, fp16=fp16)
    return {
        "text": result["text"].strip(),
        "language": result.get("language", "unknown"),
    }
