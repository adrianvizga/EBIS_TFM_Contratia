import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime
from services.usage_service import (
    get_usage,
    can_generate_contract,
    can_analyze_contract,
    can_modify_with_ai,
    has_agent_access,
    increment_contracts_generated,
    increment_contracts_analyzed,
    reserve_contract_analysis,
    increment_ai_modifications,
    PLAN_LIMITS,
)

pytestmark = pytest.mark.unit


def _mock_usage_row(generated=0, analyzed=0, ai_mods=None, gen_reached=None, ana_reached=None):
    return {
        "contracts_generated": generated,
        "contracts_analyzed": analyzed,
        "ai_modifications": ai_mods or {},
        "generation_limit_reached_at": gen_reached,
        "analysis_limit_reached_at": ana_reached,
    }


class TestAgentAccess:

    def test_free_no_agent_access(self):
        assert has_agent_access("1") is False

    def test_plus_agent_access(self):
        assert has_agent_access("2") is True

    def test_pro_agent_access(self):
        assert has_agent_access("3") is True

    def test_admin_agent_access(self):
        assert has_agent_access("0") is True


class TestGenerationLimits:

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_admin_can_always_generate(self, mock_update, mock_insert, mock_query):
        assert can_generate_contract("usr-admin", "0") is True

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_free_can_generate_within_limit(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row(generated=0)]
        assert can_generate_contract("usr-free", "1") is True

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_free_cannot_generate_over_limit(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row(generated=1, gen_reached=datetime.now())]
        assert can_generate_contract("usr-free", "1") is False

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_plus_generation_limit_10(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row(generated=9)]
        assert can_generate_contract("usr-plus", "2") is True

        mock_query.return_value = [_mock_usage_row(generated=10, gen_reached=datetime.now())]
        assert can_generate_contract("usr-plus", "2") is False

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_pro_generation_limit_30(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row(generated=29)]
        assert can_generate_contract("usr-pro", "3") is True

        mock_query.return_value = [_mock_usage_row(generated=30, gen_reached=datetime.now())]
        assert can_generate_contract("usr-pro", "3") is False


class TestAnalysisLimits:

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_free_analysis_limit_3(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row(analyzed=2)]
        assert can_analyze_contract("usr-free", "1") is True

        mock_query.return_value = [_mock_usage_row(analyzed=3, ana_reached=datetime.now())]
        assert can_analyze_contract("usr-free", "1") is False

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_plus_analysis_limit_10(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row(analyzed=9)]
        assert can_analyze_contract("usr-plus", "2") is True

        mock_query.return_value = [_mock_usage_row(analyzed=10, ana_reached=datetime.now())]
        assert can_analyze_contract("usr-plus", "2") is False

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_pro_analysis_limit_25(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row(analyzed=24)]
        assert can_analyze_contract("usr-pro", "3") is True

        mock_query.return_value = [_mock_usage_row(analyzed=25, ana_reached=datetime.now())]
        assert can_analyze_contract("usr-pro", "3") is False


class TestAIModificationLimits:

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_ai_mods_free_limit_3(self, mock_update, mock_insert, mock_query):
        contract_id = "contract-abc"
        mock_query.return_value = [_mock_usage_row(ai_mods={contract_id: 2})]
        assert can_modify_with_ai("usr-free", "1", contract_id) is True

        mock_query.return_value = [_mock_usage_row(ai_mods={contract_id: 3})]
        assert can_modify_with_ai("usr-free", "1", contract_id) is False

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_ai_mods_plus_limit_30(self, mock_update, mock_insert, mock_query):
        contract_id = "contract-abc"
        mock_query.return_value = [_mock_usage_row(ai_mods={contract_id: 29})]
        assert can_modify_with_ai("usr-plus", "2", contract_id) is True

        mock_query.return_value = [_mock_usage_row(ai_mods={contract_id: 30})]
        assert can_modify_with_ai("usr-plus", "2", contract_id) is False

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_ai_mods_pro_limit_50(self, mock_update, mock_insert, mock_query):
        contract_id = "contract-abc"
        mock_query.return_value = [_mock_usage_row(ai_mods={contract_id: 49})]
        assert can_modify_with_ai("usr-pro", "3", contract_id) is True

        mock_query.return_value = [_mock_usage_row(ai_mods={contract_id: 50})]
        assert can_modify_with_ai("usr-pro", "3", contract_id) is False


class TestIncrementCounters:

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_increment_generation_counter(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [{"id": "row-1"}]
        mock_insert.return_value = {"id": "row-1"}
        mock_query.side_effect = [
            [{"id": "row-1"}],
            [{"contracts_generated": 1, "generation_limit_reached_at": None}],
        ]
        increment_contracts_generated("usr-test", "1")
        assert mock_insert.call_count >= 1
        call_args = mock_insert.call_args_list[0]
        assert "contracts_generated" in call_args[0][0]

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_increment_analysis_counter(self, mock_update, mock_insert, mock_query):
        mock_query.side_effect = [
            [{"id": "row-1"}],
            [{"contracts_analyzed": 1, "analysis_limit_reached_at": None}],
        ]
        mock_insert.return_value = {"id": "row-1"}
        increment_contracts_analyzed("usr-test", "1")
        assert mock_insert.call_count >= 1
        call_args = mock_insert.call_args_list[0]
        assert "contracts_analyzed" in call_args[0][0]

    @patch("services.usage_service.execute_insert_returning")
    def test_reserve_analysis_is_atomic_and_succeeds(self, mock_insert):
        mock_insert.side_effect = [{"id": "row-1"}, {"id": "row-1"}]
        assert reserve_contract_analysis("usr-test", "1") is True
        assert "contracts_analyzed <" in mock_insert.call_args_list[1][0][0]
        assert mock_insert.call_args_list[1][0][1]["limit"] == 3

    @patch("services.usage_service.execute_insert_returning")
    def test_reserve_analysis_rejects_when_limit_won_race(self, mock_insert):
        mock_insert.side_effect = [{"id": "row-1"}, None]
        assert reserve_contract_analysis("usr-test", "1") is False

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_increment_ai_mods_jsonb(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [{"id": "row-1"}]
        mock_insert.return_value = {"id": "row-1"}
        increment_ai_modifications("usr-test", "contract-xyz")
        assert mock_insert.call_count >= 1
        call_args = mock_insert.call_args_list[0]
        assert "ai_modifications" in call_args[0][0]


class TestGetUsageStructure:

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_get_usage_structure(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row(generated=1, analyzed=2)]
        result = get_usage("usr-test", "1")
        assert "plan" in result
        assert "contracts_generated" in result
        assert "contracts_generated_limit" in result
        assert "contracts_analyzed" in result
        assert "contracts_analyzed_limit" in result
        assert "ai_modifications" in result
        assert "period_start" in result
        assert "role" in result

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_get_usage_correct_limits_free(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row()]
        result = get_usage("usr-test", "1")
        assert result["contracts_generated_limit"] == 1
        assert result["contracts_analyzed_limit"] == 3
        assert result["ai_modifications_per_contract_limit"] == 3
        assert result["agent_access"] is False

    @patch("services.usage_service.execute_query")
    @patch("services.usage_service.execute_insert_returning")
    @patch("services.usage_service.execute_update")
    def test_get_usage_correct_limits_admin(self, mock_update, mock_insert, mock_query):
        mock_query.return_value = [_mock_usage_row()]
        result = get_usage("usr-admin", "0")
        assert result["contracts_generated_limit"] is None
        assert result["contracts_analyzed_limit"] is None
        assert result["agent_access"] is True
