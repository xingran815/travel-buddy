import whisper


def transcribe(audio_path: str, model_name: str = "small") -> dict:
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path)
    return {
        "text": result["text"].strip(),
        "language": result.get("language", "unknown"),
    }
