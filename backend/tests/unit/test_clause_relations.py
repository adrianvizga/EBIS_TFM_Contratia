import pytest
from unittest.mock import patch, MagicMock
import json
from services.clause_relations_service import (
    detect_absent_clause_references,
    analyze_clause_relations,
)

pytestmark = pytest.mark.unit


def _make_clause(id, number, text="", explanation=""):
    return {
        "id": id,
        "clause_number": number,
        "title": f"Cláusula {number}",
        "original_text": text,
        "plain_explanation": explanation,
    }


class TestDetectAbsentReferences:

    def test_detect_absent_ref_found(self):
        clauses = [_make_clause(f"c{i}", str(i)) for i in range(1, 6)]
        clauses[0]["original_text"] = "según cláusula 12 del presente contrato"
        result = detect_absent_clause_references(clauses)
        assert len(result) >= 1
        refs = [r["referenced_number"] for r in result]
        assert "12" in refs

    def test_detect_absent_ref_existing(self):
        clauses = [_make_clause(f"c{i}", str(i)) for i in range(1, 6)]
        clauses[0]["original_text"] = "según cláusula 3 del presente contrato"
        result = detect_absent_clause_references(clauses)
        refs = [r["referenced_number"] for r in result]
        assert "3" not in refs

    def test_detect_absent_ref_multiple(self):
        clauses = [_make_clause(f"c{i}", str(i)) for i in range(1, 4)]
        clauses[0]["original_text"] = "ver cláusula 10 y cláusula 15"
        result = detect_absent_clause_references(clauses)
        refs = [r["referenced_number"] for r in result]
        assert "10" in refs
        assert "15" in refs

    def test_detect_absent_ref_no_refs(self):
        clauses = [_make_clause(f"c{i}", str(i), text="Sin referencias cruzadas aquí") for i in range(1, 4)]
        result = detect_absent_clause_references(clauses)
        assert result == []

    def test_detect_deduplicates(self):
        clauses = [_make_clause("c1", "1")]
        clauses[0]["original_text"] = "según cláusula 99 y conforme a cláusula 99"
        result = detect_absent_clause_references(clauses)
        refs = [r["referenced_number"] for r in result]
        assert refs.count("99") == 1


class TestAnalyzeClauseRelations:

    @patch("services.clause_relations_service.settings")
    def test_no_api_key_returns_empty(self, mock_settings):
        mock_settings.openai_api_key = ""
        result, tokens = analyze_clause_relations([_make_clause("c1", "1")])
        assert result == []
        assert tokens == 0

    def test_empty_clauses_returns_empty(self):
        with patch("services.clause_relations_service.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            result, tokens = analyze_clause_relations([])
            assert result == []
            assert tokens == 0

    @patch("services.clause_relations_service.OpenAI")
    @patch("services.clause_relations_service.settings")
    def test_analyze_batch_split(self, mock_settings, mock_openai_cls):
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "test-relations-model"
        clauses = [_make_clause(f"c{i}", str(i), text=f"Texto cláusula {i}") for i in range(1, 21)]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"relations": []})
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        result, tokens = analyze_clause_relations(clauses)
        assert mock_client.chat.completions.create.call_count == 1

    @patch("services.clause_relations_service.OpenAI")
    @patch("services.clause_relations_service.settings")
    def test_analyze_deduplication(self, mock_settings, mock_openai_cls):
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "test-relations-model"
        clauses = [_make_clause(f"c{i}", str(i), text=f"Texto {i}") for i in range(1, 6)]

        relations = [
            {"type": "dependency", "from_index": 1, "to_index": 2, "severity": "medium",
             "title": "Rel 1", "description": "Desc 1"},
            {"type": "dependency", "from_index": 1, "to_index": 2, "severity": "high",
             "title": "Rel 1 dup", "description": "Duplicate"},
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"relations": relations})
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 200

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        result, tokens = analyze_clause_relations(clauses)
        dep_count = sum(1 for r in result if r["type"] == "dependency"
                        and set([r["from_clause_id"], r["to_clause_id"]]) == {"c1", "c2"})
        assert dep_count == 1
