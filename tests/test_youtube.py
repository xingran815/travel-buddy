"""Tests for YouTube audio download, title fetching, transcription, and cleanup."""

from unittest.mock import patch, MagicMock
import os
import pytest
from app.youtube.downloader import download_audio, get_video_title, cleanup
from app.youtube.transcriber import transcribe


class TestDownloader:
    @patch("app.youtube.downloader.yt_dlp.YoutubeDL")
    def test_download_audio_returns_wav_path_and_video_id(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {"id": "abc123", "title": "Test Video"}

        with patch("os.path.exists", return_value=True):
            filepath, video_id = download_audio("https://youtube.com/watch?v=abc123")
        assert filepath.endswith("abc123.wav")
        assert "downloads" in filepath
        assert video_id == "abc123"

    @patch("app.youtube.downloader.yt_dlp.YoutubeDL")
    def test_get_video_title(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {"id": "abc123", "title": "Istanbul Travel Guide"}

        result = get_video_title("https://youtube.com/watch?v=abc123")
        assert result == "Istanbul Travel Guide"

    @patch("app.youtube.downloader.yt_dlp.YoutubeDL")
    def test_download_audio_uses_worst_quality(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {"id": "abc123", "title": "Test"}

        with patch("os.path.exists", return_value=True):
            download_audio("https://youtube.com/watch?v=abc123")

        call_args = mock_ydl_cls.call_args[0][0] if mock_ydl_cls.call_args[0] else mock_ydl_cls.call_args[1]
        if isinstance(call_args, dict):
            assert "worst" in call_args.get("format", "")

    @patch("app.youtube.downloader.glob.glob")
    @patch("app.youtube.downloader.os.remove")
    def test_cleanup_removes_all_files_for_video_id(self, mock_remove, mock_glob):
        mock_glob.return_value = ["downloads/abc123.wav", "downloads/abc123.webm"]
        cleanup("abc123")
        assert mock_remove.call_count == 2

    @patch("app.youtube.downloader.glob.glob")
    @patch("app.youtube.downloader.os.remove")
    def test_cleanup_no_files(self, mock_remove, mock_glob):
        mock_glob.return_value = []
        cleanup("nonexistent")
        mock_remove.assert_not_called()


class TestTranscriber:
    @patch("app.youtube.transcriber.whisper.load_model")
    def test_transcribe_returns_text_and_language(self, mock_load_model):
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        mock_model.transcribe.return_value = {
            "text": "  Istanbul is a beautiful city.  ",
            "language": "en",
        }

        result = transcribe("/fake/audio.wav")
        assert result["text"] == "Istanbul is a beautiful city."
        assert result["language"] == "en"

    @patch("app.youtube.transcriber.whisper.load_model")
    def test_transcribe_uses_small_model(self, mock_load_model):
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        mock_model.transcribe.return_value = {"text": "test", "language": "tr"}

        transcribe("/fake/audio.wav")
        mock_load_model.assert_called_with("small")

    @patch("app.youtube.transcriber.whisper.load_model")
    def test_transcribe_custom_model_name(self, mock_load_model):
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        mock_model.transcribe.return_value = {"text": "test", "language": "en"}

        transcribe("/fake/audio.wav", model_name="base")
        mock_load_model.assert_called_with("base")

    @patch("app.youtube.transcriber.whisper.load_model")
    def test_transcribe_unknown_language(self, mock_load_model):
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        mock_model.transcribe.return_value = {"text": "test", "language": "unknown"}

        result = transcribe("/fake/audio.wav")
        assert result["language"] == "unknown"
