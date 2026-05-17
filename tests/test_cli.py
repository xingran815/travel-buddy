from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from main import cli


class TestSummarizeCommand:
    @patch("main.cleanup")
    @patch("main.summarize_in_turkish", return_value="İstanbul güzel bir şehirdir.")
    @patch("main.translate_to_turkish", return_value="İstanbul güzel bir şehir.")
    @patch("main.transcribe", return_value={"text": "Istanbul is beautiful.", "language": "en"})
    @patch("main.get_video_title", return_value="Istanbul Guide")
    @patch("main.download_audio", return_value=("/tmp/test.wav", "test123"))
    def test_summarize_turkish_output(self, mock_dl, mock_title, mock_transcribe, mock_translate, mock_summarize, mock_cleanup):
        runner = CliRunner()
        result = runner.invoke(cli, ["--lang", "tr", "summarize", "https://youtube.com/watch?v=test"])
        assert result.exit_code == 0
        assert "İstanbul güzel bir şehir." in result.output
        assert "İstanbul güzel bir şehirdir." in result.output
        mock_cleanup.assert_called_with("test123")

    @patch("main.cleanup")
    @patch("main.summarize_in_turkish", return_value="Summary in Turkish.")
    @patch("main.translate_to_turkish", return_value="Translated text.")
    @patch("main.transcribe", return_value={"text": "Some text.", "language": "en"})
    @patch("main.get_video_title", return_value="Test Video")
    @patch("main.download_audio", return_value=("/tmp/test.wav", "test123"))
    def test_summarize_english_output(self, mock_dl, mock_title, mock_transcribe, mock_translate, mock_summarize, mock_cleanup):
        runner = CliRunner()
        result = runner.invoke(cli, ["--lang", "en", "summarize", "https://youtube.com/watch?v=test"])
        assert result.exit_code == 0
        assert "Translated text." in result.output
        assert "Summary in Turkish." in result.output
        assert "Turkish Translation" in result.output


class TestRecommendCommand:
    @patch("main.recommend_places", return_value=[
        {"name": "Nusr-Et", "rating": 4.5, "address": "Istanbul", "price_level": 3, "website": "https://nusr-et.com", "reviews": [{"author": "John", "rating": 5, "text": "Great!"}]},
    ])
    def test_recommend_turkish(self, mock_rec):
        runner = CliRunner()
        result = runner.invoke(cli, ["--lang", "tr", "recommend", "Istanbul"])
        assert result.exit_code == 0
        assert "Nusr-Et" in result.output
        assert "Puan" in result.output

    @patch("main.recommend_places", return_value=[
        {"name": "Nusr-Et", "rating": 4.5, "address": "Istanbul", "price_level": 3, "website": "https://nusr-et.com", "reviews": [{"author": "John", "rating": 5, "text": "Great!"}]},
    ])
    def test_recommend_english(self, mock_rec):
        runner = CliRunner()
        result = runner.invoke(cli, ["--lang", "en", "recommend", "Istanbul"])
        assert result.exit_code == 0
        assert "Rating" in result.output

    @patch("main.recommend_places", return_value=[])
    def test_recommend_no_results(self, mock_rec):
        runner = CliRunner()
        result = runner.invoke(cli, ["--lang", "en", "recommend", "Nowhere"])
        assert result.exit_code == 0
        assert "0" in result.output


class TestPlanCommand:
    @patch("main.generate_plan", return_value="1. Gün: Sultanahmet...")
    @patch("main.recommend_places", return_value=[{"name": "Test Rest", "rating": 4.0, "address": "Istanbul", "reviews": []}])
    def test_plan_without_url(self, mock_rec, mock_plan):
        runner = CliRunner()
        result = runner.invoke(cli, ["--lang", "tr", "plan", "Istanbul", "--budget", "500", "--days", "3"])
        assert result.exit_code == 0
        assert "1. Gün" in result.output

    @patch("main.cleanup")
    @patch("main.generate_plan", return_value="Day 1: Visit museum...")
    @patch("main.recommend_places", return_value=[])
    @patch("main.summarize_in_turkish", return_value="Video summary.")
    @patch("main.translate_to_turkish", return_value="Translated.")
    @patch("main.transcribe", return_value={"text": "Text", "language": "en"})
    @patch("main.get_video_title", return_value="Istanbul Guide")
    @patch("main.download_audio", return_value=("/tmp/test.wav", "test123"))
    def test_plan_with_url(self, mock_dl, mock_title, mock_transcribe, mock_translate, mock_summarize, mock_rec, mock_plan, mock_cleanup):
        runner = CliRunner()
        result = runner.invoke(cli, ["--lang", "en", "plan", "Istanbul", "--url", "https://youtube.com/watch?v=test"])
        assert result.exit_code == 0
        assert "Day 1" in result.output
        assert "Translated." in result.output
        mock_cleanup.assert_called_with("test123")


class TestCliHelp:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "summarize" in result.output
        assert "recommend" in result.output
        assert "plan" in result.output

    def test_summarize_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["summarize", "--help"])
        assert result.exit_code == 0

    def test_plan_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["plan", "--help"])
        assert result.exit_code == 0
        assert "--budget" in result.output
        assert "--days" in result.output
