import sys
import os
import json
import uuid
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))



def _contract_row(overrides=None):
    row = {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "original_file_name": "contrato_test.pdf",
        "storage_path": "/tmp/contrato.pdf",
        "mime_type": "application/pdf",
        "status": "pending",
        "contract_type": None,
        "language": None,
        "page_count": None,
        "overall_risk": None,
        "error_message": None,
    }
    if overrides:
        row.update(overrides)
    return row


def _gen_contract_row(overrides=None):
    row = {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "title": "Contrato de arrendamiento",
        "contract_type": "arrendamiento_vivienda",
        "contract_details": {"parties": {"partyA": "Juan", "partyB": "Ana"}, "description": "Piso"},
        "current_content": "",
        "status": "pending",
    }
    if overrides:
        row.update(overrides)
    return row


def _analysis_result():
    return {
        "contract_metadata": {
            "detected_language": "es",
            "contract_type": "arrendamiento_vivienda",
            "subtype": "vivienda_habitual",
            "jurisdiction": "España",
            "governing_law": "LAU",
            "page_count_estimate": 5
        },
        "analysis_overview": {
            "overall_risk": "none",
            "summary": "Contrato estándar de arrendamiento.",
            "tokens_used_hint": 1200
        },
        "clauses": [
            {
                "clause_id": "c1", "clause_number": "1", "title": "Objeto",
                "original_text": "Se arrienda el inmueble...",
                "plain_explanation": "Descripción del inmueble",
                "legal_advice": None, "risk_level": "none", "has_issue": False,
                "category": "objeto", "subcategories": [], "order_index": 0
            },
            {
                "clause_id": "c2", "clause_number": "2", "title": "Renta",
                "original_text": "La renta mensual será de 800€...",
                "plain_explanation": "Precio del alquiler",
                "legal_advice": None, "risk_level": "none", "has_issue": False,
                "category": "renta", "subcategories": [], "order_index": 1
            },
        ]
    }


def _clause_legal_result(risk="none", has_issue=False):
    return {
        "clause_result": {
            "risk_level": risk,
            "has_issue": has_issue,
            "plain_explanation": "Análisis de la cláusula",
            "legal_advice": "Según art. 36 LAU..." if has_issue else None
        },
        "risks_to_create": [
            {"title": "Riesgo detectado", "description": "Desc", "severity": "medium", "category": "fianza"}
        ] if has_issue else [],
        "positive_aspects_to_create": [],
        "tokens_used": 200
    }


def _aggregation_result():
    return {
        "overall_risk": "low",
        "summary": "Contrato con riesgo bajo en general.",
        "missing_elements_to_create": [
            {"title": "Inventario", "description": "Falta inventario de bienes",
             "suggested_clause": "Añadir anexo de inventario",
             "severity": "low", "category": "otra"}
        ],
        "tokens_used": 300
    }



@pytest.mark.integration
class TestAnalyzeContractTask:

    def _setup_cursor(self, contract, analysis_id=None):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetchone_results = []
        fetchall_results = []

        fetchone_results.append(contract)
        if analysis_id:
            fetchone_results.append({"id": analysis_id})
        else:
            fetchone_results.append(None)
        clause_rows = [
            {"id": str(uuid.uuid4()), "clause_number": "1", "title": "Objeto",
             "original_text": "Se arrienda...", "plain_explanation": "Desc", "risk_level": "none"},
            {"id": str(uuid.uuid4()), "clause_number": "2", "title": "Renta",
             "original_text": "La renta será...", "plain_explanation": "Precio", "risk_level": "none"},
        ]
        fetchall_results.append(clause_rows)
        fetchall_results.append(clause_rows)

        mock_cursor.fetchone.side_effect = fetchone_results
        mock_cursor.fetchall.side_effect = fetchall_results

        return mock_conn, mock_cursor, clause_rows

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.analyze_clause_relations', return_value=([], 0))
    @patch('workers.tasks.detect_absent_clause_references', return_value=[])
    @patch('workers.tasks.aggregate_analysis')
    @patch('workers.tasks.retrieve_legal_context', return_value=[])
    @patch('workers.tasks.analyze_clause_legal')
    @patch('workers.tasks.analyze_contract_with_openai')
    @patch('workers.tasks.extract_text_from_file', return_value="Texto del contrato completo...")
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_analyze_contract_full_pipeline(self, mock_get_conn, mock_release,
                                            mock_extract, mock_openai, mock_legal,
                                            mock_rag, mock_aggregate,
                                            mock_absent, mock_relations,
                                            mock_notify):
        contract = _contract_row()
        analysis_id = str(uuid.uuid4())
        mock_conn, mock_cursor, clause_rows = self._setup_cursor(contract, analysis_id)
        mock_get_conn.return_value = mock_conn

        mock_openai.return_value = _analysis_result()
        mock_legal.return_value = _clause_legal_result()
        mock_aggregate.return_value = _aggregation_result()

        from workers.tasks import analyze_contract
        result = analyze_contract(contract["id"])

        assert result["status"] == "success"
        assert result["clauses_analyzed"] == 2
        mock_conn.commit.assert_called()

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.analyze_clause_relations', return_value=([], 0))
    @patch('workers.tasks.detect_absent_clause_references', return_value=[])
    @patch('workers.tasks.aggregate_analysis')
    @patch('workers.tasks.retrieve_legal_context', return_value=[])
    @patch('workers.tasks.analyze_clause_legal')
    @patch('workers.tasks.analyze_contract_with_openai')
    @patch('workers.tasks.extract_text_from_file', return_value="Texto extraído")
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_analyze_contract_extracts_text(self, mock_get_conn, mock_release,
                                            mock_extract, mock_openai, mock_legal,
                                            mock_rag, mock_aggregate,
                                            mock_absent, mock_relations,
                                            mock_notify):
        contract = _contract_row()
        mock_conn, _, _ = self._setup_cursor(contract, str(uuid.uuid4()))
        mock_get_conn.return_value = mock_conn
        mock_openai.return_value = _analysis_result()
        mock_legal.return_value = _clause_legal_result()
        mock_aggregate.return_value = _aggregation_result()

        from workers.tasks import analyze_contract
        analyze_contract(contract["id"])

        mock_extract.assert_called_once_with(contract["storage_path"], contract["mime_type"])

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.analyze_clause_relations', return_value=([], 0))
    @patch('workers.tasks.detect_absent_clause_references', return_value=[])
    @patch('workers.tasks.aggregate_analysis')
    @patch('workers.tasks.retrieve_legal_context', return_value=[])
    @patch('workers.tasks.analyze_clause_legal')
    @patch('workers.tasks.analyze_contract_with_openai')
    @patch('workers.tasks.extract_text_from_file', return_value="Texto")
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_analyze_contract_calls_openai(self, mock_get_conn, mock_release,
                                           mock_extract, mock_openai, mock_legal,
                                           mock_rag, mock_aggregate,
                                           mock_absent, mock_relations,
                                           mock_notify):
        contract = _contract_row()
        mock_conn, _, _ = self._setup_cursor(contract, str(uuid.uuid4()))
        mock_get_conn.return_value = mock_conn
        mock_openai.return_value = _analysis_result()
        mock_legal.return_value = _clause_legal_result()
        mock_aggregate.return_value = _aggregation_result()

        from workers.tasks import analyze_contract
        analyze_contract(contract["id"])

        mock_openai.assert_called_once_with("Texto", user_id=contract["user_id"])

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.analyze_clause_relations', return_value=([], 0))
    @patch('workers.tasks.detect_absent_clause_references', return_value=[])
    @patch('workers.tasks.aggregate_analysis')
    @patch('workers.tasks.retrieve_legal_context', return_value=[])
    @patch('workers.tasks.analyze_clause_legal')
    @patch('workers.tasks.analyze_contract_with_openai')
    @patch('workers.tasks.extract_text_from_file', return_value="Texto")
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_analyze_contract_inserts_clauses(self, mock_get_conn, mock_release,
                                              mock_extract, mock_openai, mock_legal,
                                              mock_rag, mock_aggregate,
                                              mock_absent, mock_relations,
                                              mock_notify):
        contract = _contract_row()
        mock_conn, mock_cursor, _ = self._setup_cursor(contract, str(uuid.uuid4()))
        mock_get_conn.return_value = mock_conn
        mock_openai.return_value = _analysis_result()
        mock_legal.return_value = _clause_legal_result()
        mock_aggregate.return_value = _aggregation_result()

        from workers.tasks import analyze_contract
        analyze_contract(contract["id"])

        insert_calls = [
            c for c in mock_cursor.execute.call_args_list
            if "INSERT INTO contract_clauses" in str(c)
        ]
        assert len(insert_calls) == 2

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.analyze_clause_relations', return_value=([], 0))
    @patch('workers.tasks.detect_absent_clause_references', return_value=[])
    @patch('workers.tasks.aggregate_analysis')
    @patch('workers.tasks.retrieve_legal_context', return_value=[])
    @patch('workers.tasks.analyze_clause_legal')
    @patch('workers.tasks.analyze_contract_with_openai')
    @patch('workers.tasks.extract_text_from_file', return_value="Texto")
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_analyze_contract_legal_per_clause(self, mock_get_conn, mock_release,
                                               mock_extract, mock_openai, mock_legal,
                                               mock_rag, mock_aggregate,
                                               mock_absent, mock_relations,
                                               mock_notify):
        contract = _contract_row()
        mock_conn, _, clause_rows = self._setup_cursor(contract, str(uuid.uuid4()))
        mock_get_conn.return_value = mock_conn
        mock_openai.return_value = _analysis_result()
        mock_legal.return_value = _clause_legal_result()
        mock_aggregate.return_value = _aggregation_result()

        from workers.tasks import analyze_contract
        analyze_contract(contract["id"])

        assert mock_legal.call_count == len(clause_rows)

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.analyze_clause_relations', return_value=([], 0))
    @patch('workers.tasks.detect_absent_clause_references', return_value=[{"from_clause_id": "x", "referenced_number": "99", "clause_title": "T"}])
    @patch('workers.tasks.aggregate_analysis')
    @patch('workers.tasks.retrieve_legal_context', return_value=[])
    @patch('workers.tasks.analyze_clause_legal')
    @patch('workers.tasks.analyze_contract_with_openai')
    @patch('workers.tasks.extract_text_from_file', return_value="Texto")
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_analyze_contract_detects_relations(self, mock_get_conn, mock_release,
                                                mock_extract, mock_openai, mock_legal,
                                                mock_rag, mock_aggregate,
                                                mock_absent, mock_relations,
                                                mock_notify):
        contract = _contract_row()
        mock_conn, mock_cursor, _ = self._setup_cursor(contract, str(uuid.uuid4()))
        mock_get_conn.return_value = mock_conn
        mock_openai.return_value = _analysis_result()
        mock_legal.return_value = _clause_legal_result()
        mock_aggregate.return_value = _aggregation_result()

        from workers.tasks import analyze_contract
        result = analyze_contract(contract["id"])

        mock_absent.assert_called_once()
        mock_relations.assert_called_once()
        assert result["relations_found"] == 1

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.analyze_clause_relations', return_value=([], 0))
    @patch('workers.tasks.detect_absent_clause_references', return_value=[])
    @patch('workers.tasks.aggregate_analysis')
    @patch('workers.tasks.retrieve_legal_context', return_value=[])
    @patch('workers.tasks.analyze_clause_legal')
    @patch('workers.tasks.analyze_contract_with_openai')
    @patch('workers.tasks.extract_text_from_file', return_value="Texto")
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_analyze_contract_notifies_user(self, mock_get_conn, mock_release,
                                            mock_extract, mock_openai, mock_legal,
                                            mock_rag, mock_aggregate,
                                            mock_absent, mock_relations,
                                            mock_notify):
        contract = _contract_row()
        mock_conn, _, _ = self._setup_cursor(contract, str(uuid.uuid4()))
        mock_get_conn.return_value = mock_conn
        mock_openai.return_value = _analysis_result()
        mock_legal.return_value = _clause_legal_result()
        mock_aggregate.return_value = _aggregation_result()

        from workers.tasks import analyze_contract
        analyze_contract(contract["id"])

        assert mock_notify.call_count >= 2
        last_call_kwargs = mock_notify.call_args_list[-1]
        assert "completado" in str(last_call_kwargs).lower() or "success" in str(last_call_kwargs).lower()

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.extract_text_from_file', side_effect=ValueError("Cannot extract"))
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_analyze_contract_error_sets_status(self, mock_get_conn, mock_release,
                                                mock_extract, mock_notify):
        contract = _contract_row()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = contract
        mock_get_conn.return_value = mock_conn

        from workers.tasks import analyze_contract
        with pytest.raises(ValueError):
            analyze_contract(contract["id"])

        error_calls = [
            c for c in mock_cursor.execute.call_args_list
            if "status = 'error'" in str(c)
        ]
        assert len(error_calls) >= 1

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.extract_text_from_file', side_effect=RuntimeError("Extraction failed"))
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_analyze_contract_error_notifies(self, mock_get_conn, mock_release,
                                             mock_extract, mock_notify):
        contract = _contract_row()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = contract
        mock_get_conn.return_value = mock_conn

        from workers.tasks import analyze_contract
        with pytest.raises(RuntimeError):
            analyze_contract(contract["id"])

        error_notify_calls = [
            c for c in mock_notify.call_args_list
            if "error" in str(c).lower()
        ]
        assert len(error_notify_calls) >= 1



@pytest.mark.integration
class TestGenerateContractTask:

    @patch('services.generated_contracts_repository.complete_generation', return_value=({}, True))
    @patch('services.contract_generation.validate_generated_draft')
    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.time.sleep')
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_generate_contract_task_success(self, mock_get_conn, mock_release,
                                            mock_sleep, mock_notify, mock_validate, mock_complete):
        contract = _gen_contract_row()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [contract]
        mock_get_conn.return_value = mock_conn
        mock_validate.return_value.valid = True

        with patch('services.openai_client.generate_contract_content', return_value="CONTRATO GENERADO POR IA") as mock_gen:
            from workers.tasks import generate_contract_task
            generate_contract_task(contract["id"])

        mock_gen.assert_called_once()

        mock_complete.assert_called_once()

        mock_conn.commit.assert_called()

    @patch('workers.tasks.create_notification')
    @patch('workers.tasks.time.sleep')
    @patch('workers.tasks.release_connection')
    @patch('workers.tasks.get_connection')
    def test_generate_contract_task_error(self, mock_get_conn, mock_release,
                                          mock_sleep, mock_notify):
        contract = _gen_contract_row()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = contract
        mock_get_conn.return_value = mock_conn

        with patch('services.openai_client.generate_contract_content', side_effect=RuntimeError("OpenAI down")):
            from workers.tasks import generate_contract_task
            with pytest.raises(RuntimeError):
                generate_contract_task(contract["id"])

        error_calls = [
            c for c in mock_cursor.execute.call_args_list
            if "status='error'" in str(c)
        ]
        assert len(error_calls) >= 1
