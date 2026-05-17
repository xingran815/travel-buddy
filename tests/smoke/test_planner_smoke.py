import pytest
from app.planner.generator import generate_plan
from app.config import LLM_API_KEY


@pytest.mark.smoke
class TestPlannerSmoke:
    def test_generate_plan_real(self):
        if not LLM_API_KEY or LLM_API_KEY == "your_api_key_here":
            pytest.skip("LLM_API_KEY not configured")
        result = generate_plan("Istanbul", 500, 2, preferences="history, food", lang="tr")
        assert len(result) > 50
