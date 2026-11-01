import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.unit


class TestGetUserSeed:

    def test_returns_42_for_empty_user_id(self):
        from core.utils import get_user_seed
        assert get_user_seed("") == 42
        assert get_user_seed(None) == 42

    def test_returns_crc32_for_non_empty_user_id(self):
        from core.utils import get_user_seed
        result = get_user_seed("user-123")
        assert isinstance(result, int)
        assert result != 42

    def test_same_user_same_seed(self):
        from core.utils import get_user_seed
        assert get_user_seed("abc") == get_user_seed("abc")


class TestEnqueueContractAnalysis:

    def test_enqueue_returns_task_id(self):
        mock_task = MagicMock()
        mock_task.id = "task-abc"
        with patch("workers.tasks.analyze_contract") as mock_analyze:
            mock_analyze.delay.return_value = mock_task
            from services.contracts.contracts_service import enqueue_contract_analysis
            result = enqueue_contract_analysis(42)
        assert result == "task-abc"
        mock_analyze.delay.assert_called_once_with(42)


class TestGetOpenaiClient:

    def test_raises_when_key_missing(self):
        from services.legal_analysis import get_openai_client
        with patch("services.legal_analysis.settings") as mock_settings:
            mock_settings.openai_api_key = None
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                get_openai_client()

    def test_returns_client_when_key_present(self):
        from services.legal_analysis import get_openai_client
        with patch("services.legal_analysis.settings") as mock_settings, \
             patch("services.legal_analysis.OpenAI") as mock_openai:
            mock_settings.openai_api_key = "sk-test"
            get_openai_client()
        mock_openai.assert_called_once_with(api_key="sk-test")


class TestMapRiskToSeverity:

    def test_none_maps_to_low(self):
        from services.legal_analysis import map_risk_to_severity
        assert map_risk_to_severity("none") == "low"

    def test_low_maps_to_low(self):
        from services.legal_analysis import map_risk_to_severity
        assert map_risk_to_severity("low") == "low"

    def test_medium_maps_to_medium(self):
        from services.legal_analysis import map_risk_to_severity
        assert map_risk_to_severity("medium") == "medium"

    def test_high_maps_to_high(self):
        from services.legal_analysis import map_risk_to_severity
        assert map_risk_to_severity("high") == "high"

    def test_critical_maps_to_high(self):
        from services.legal_analysis import map_risk_to_severity
        assert map_risk_to_severity("critical") == "high"

    def test_unknown_defaults_to_low(self):
        from services.legal_analysis import map_risk_to_severity
        assert map_risk_to_severity("unknown_value") == "low"
