import pytest
from pydantic import ValidationError

from models.contract_analysis import (
    ClauseLegalAnalysis,
    ClauseRelationsAnalysis,
    InitialContractAnalysis,
)


def _initial_payload():
    return {
        "contract_metadata": {
            "detected_language": "es",
            "contract_type": "arrendamiento_vivienda",
            "subtype": "vivienda_habitual",
            "jurisdiction": "España",
            "governing_law": "LAU",
            "page_count_estimate": 2,
        },
        "analysis_overview": {"overall_risk": "none", "summary": "Resumen", "tokens_used_hint": None},
        "clauses": [{
            "clause_id": "c1", "clause_number": "1", "title": "Objeto",
            "original_text": "Texto contractual", "plain_explanation": "Explicación",
            "legal_advice": None, "risk_level": "none", "has_issue": False,
            "category": "objeto", "subcategories": [], "order_index": 0,
        }],
    }


def test_initial_analysis_rejects_unknown_fields():
    payload = _initial_payload()
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        InitialContractAnalysis.model_validate(payload)


def test_initial_analysis_rejects_duplicate_clause_order():
    payload = _initial_payload()
    payload["clauses"].append({**payload["clauses"][0], "clause_id": "c2"})
    with pytest.raises(ValidationError):
        InitialContractAnalysis.model_validate(payload)


def test_clause_risk_requires_issue_flag():
    with pytest.raises(ValidationError):
        ClauseLegalAnalysis.model_validate({
            "clause_result": {
                "risk_level": "high", "has_issue": False,
                "plain_explanation": "Existe un problema", "legal_advice": None,
            },
            "risks_to_create": [],
            "positive_aspects_to_create": [],
        })


def test_relations_reject_invalid_indices_and_enums():
    with pytest.raises(ValidationError):
        ClauseRelationsAnalysis.model_validate({
            "relations": [{
                "type": "related", "from_index": 0, "to_index": 2,
                "severity": "urgent", "title": "Relación", "description": "Descripción",
            }]
        })

