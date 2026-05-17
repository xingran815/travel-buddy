import torch
import whisper


def transcribe(audio_path: str, model_name: str = "small") -> dict:
    fp16 = torch.cuda.is_available()
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, fp16=fp16)
    return {
        "text": result["text"].strip(),
        "language": result.get("language", "unknown"),
    }
