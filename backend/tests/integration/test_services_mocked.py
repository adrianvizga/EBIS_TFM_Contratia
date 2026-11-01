import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))



def _openai_chat_response(content: str, total_tokens: int = 100):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    usage = MagicMock()
    usage.total_tokens = total_tokens
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


def _openai_embedding_response(vector: list = None):
    if vector is None:
        vector = [0.1] * 1536
    item = MagicMock()
    item.embedding = vector
    resp = MagicMock()
    resp.data = [item]
    return resp



@pytest.mark.integration
class TestAnalyzeContractOpenAI:

    @patch('services.openai_client.OpenAI')
    @patch('services.openai_client.settings')
    def test_analyze_contract_parses_json(self, mock_settings, mock_openai_cls):
        mock_settings.openai_api_key = "sk-test"
        mock_settings.openai_model = "test-contract-model"
        analysis = {
            "contract_metadata": {"detected_language": "es", "contract_type": "arrendamiento_vivienda",
                                  "subtype": "vivienda_habitual", "jurisdiction": "España",
                                  "governing_law": "LAU", "page_count_estimate": 3},
            "analysis_overview": {"overall_risk": "none", "summary": "Contrato estándar",
                                  "tokens_used_hint": None},
            "clauses": [{"clause_id": "c1", "clause_number": "1", "title": "Objeto",
                         "original_text": "Texto", "plain_explanation": "Explicación",
                         "legal_advice": None, "risk_level": "none", "has_issue": False,
                         "category": "objeto", "subcategories": [], "order_index": 0}]
        }
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _openai_chat_response(
            json.dumps(analysis), total_tokens=500
        )

        from services.openai_client import analyze_contract_with_openai
        result = analyze_contract_with_openai("Texto del contrato")

        assert "clauses" in result
        assert len(result["clauses"]) == 1
        assert result["analysis_overview"]["tokens_used_hint"] == 500
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "test-contract-model"

    @patch('services.openai_client.OpenAI')
    @patch('services.openai_client.settings')
    def test_analyze_contract_malformed_json(self, mock_settings, mock_openai_cls):
        mock_settings.openai_api_key = "sk-test"
        mock_settings.openai_model = "test-contract-model"
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _openai_chat_response(
            "esto no es json", total_tokens=50
        )

        from services.openai_client import analyze_contract_with_openai
        with pytest.raises(json.JSONDecodeError):
            analyze_contract_with_openai("Texto")


@pytest.mark.integration
class TestGenerateContractOpenAI:

    @patch('services.rag_service.retrieve_legal_context', return_value=[])
    @patch('services.rag_service.format_legal_context_for_prompt', return_value="")
    @patch('services.openai_client.OpenAI')
    @patch('services.openai_client.settings')
    def test_generate_contract_uses_configured_model(self, mock_settings, mock_openai_cls,
                                                      mock_fmt, mock_rag):
        mock_settings.openai_api_key = "sk-test"
        mock_settings.openai_model = "test-generation-model"
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _openai_chat_response(
            "CONTRATO DE ARRENDAMIENTO...", total_tokens=800
        )

        from services.openai_client import generate_contract_content
        result = generate_contract_content("arrendamiento_vivienda", {
            "parties": {"partyA": "Juan", "partyB": "Ana"},
            "description": "Piso en Madrid"
        })

        assert "CONTRATO" in result
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "test-generation-model"

    @patch('services.rag_service.retrieve_legal_context', return_value=[])
    @patch('services.rag_service.format_legal_context_for_prompt', return_value="")
    @patch('services.openai_client.OpenAI')
    @patch('services.openai_client.settings')
    def test_generate_contract_uses_configured_fallback(self, mock_settings, mock_openai_cls,
                                                        mock_fmt, mock_rag):
        mock_settings.openai_api_key = "sk-test"
        mock_settings.openai_model = "test-generation-model"
        mock_settings.openai_fallback_model = "test-fallback-model"
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_client.chat.completions.create.side_effect = [
            Exception("model not found"),
            _openai_chat_response("CONTRATO FALLBACK", total_tokens=600),
        ]

        from services.openai_client import generate_contract_content
        result = generate_contract_content("compraventa", {
            "parties": {"partyA": "X", "partyB": "Y"},
            "description": "Venta de local"
        })

        assert result == "CONTRATO FALLBACK"
        assert mock_client.chat.completions.create.call_count == 2
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "test-fallback-model"


@pytest.mark.integration
class TestModifyContractOpenAI:

    @patch('services.rag_service.retrieve_legal_context', return_value=[])
    @patch('services.rag_service.format_legal_context_for_prompt', return_value="")
    @patch('services.openai_client.OpenAI')
    @patch('services.openai_client.settings')
    def test_modify_contract_success(self, mock_settings, mock_openai_cls,
                                      mock_fmt, mock_rag):
        mock_settings.openai_api_key = "sk-test"
        mock_settings.openai_model = "test-modification-model"
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _openai_chat_response(
            "CONTRATO MODIFICADO...", total_tokens=900
        )

        from services.openai_client import modify_contract_content
        result = modify_contract_content(
            "contrato original...", "Añadir cláusula de penalización",
            contract_type="arrendamiento_vivienda"
        )

        assert "MODIFICADO" in result
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "test-modification-model"

    @patch('services.rag_service.retrieve_legal_context', return_value=[])
    @patch('services.rag_service.format_legal_context_for_prompt', return_value="")
    @patch('services.openai_client.OpenAI')
    @patch('services.openai_client.settings')
    def test_modify_contract_uses_configured_fallback(self, mock_settings, mock_openai_cls,
                                                       mock_fmt, mock_rag):
        mock_settings.openai_api_key = "sk-test"
        mock_settings.openai_model = "test-modification-model"
        mock_settings.openai_fallback_model = "test-fallback-model"
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            Exception("primary unavailable"),
            _openai_chat_response("CONTRATO MODIFICADO CON FALLBACK"),
        ]

        from services.openai_client import modify_contract_content
        result = modify_contract_content("original", "Modificar una cláusula")

        assert result == "CONTRATO MODIFICADO CON FALLBACK"
        assert mock_client.chat.completions.create.call_count == 2
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "test-fallback-model"

    @patch('services.openai_client.settings')
    def test_openai_api_error_propagated(self, mock_settings):
        mock_settings.openai_api_key = ""

        from services.openai_client import analyze_contract_with_openai
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            analyze_contract_with_openai("Texto")



@pytest.mark.integration
class TestAnalyzeClauseLegal:

    @patch('services.legal_analysis.get_openai_client')
    def test_analyze_clause_with_rag(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        clause_result = {
            "clause_result": {"risk_level": "low", "has_issue": True,
                              "plain_explanation": "Cláusula aceptable",
                              "legal_advice": "Según art. 36 LAU..."},
            "risks_to_create": [],
            "positive_aspects_to_create": []
        }
        mock_client.chat.completions.create.return_value = _openai_chat_response(
            json.dumps(clause_result), total_tokens=200
        )

        from services.legal_analysis import analyze_clause_legal
        legal_context = [
            {"citation": "Art. 36 LAU", "law_name": "LAU 1994",
             "law_key": "LAU_1994", "article_number": "36",
             "text": "La fianza será de una mensualidad...", "score": 0.92}
        ]
        result = analyze_clause_legal(
            {"clause_number": "5", "title": "Fianza", "original_text": "Fianza de 2 meses"},
            {"contract_type": "arrendamiento_vivienda"},
            legal_context=legal_context
        )

        assert result["clause_result"]["risk_level"] == "low"
        call_args = mock_client.chat.completions.create.call_args
        system_msg = call_args.kwargs["messages"][0]["content"] if "messages" in call_args.kwargs else call_args[1]["messages"][0]["content"]
        assert "RAG" in system_msg

    @patch('services.legal_analysis.get_openai_client')
    def test_analyze_clause_without_rag(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        clause_result = {
            "clause_result": {"risk_level": "none", "has_issue": False,
                              "plain_explanation": "Sin problemas",
                              "legal_advice": None},
            "risks_to_create": [],
            "positive_aspects_to_create": []
        }
        mock_client.chat.completions.create.return_value = _openai_chat_response(
            json.dumps(clause_result), total_tokens=150
        )

        from services.legal_analysis import analyze_clause_legal
        result = analyze_clause_legal(
            {"clause_number": "1", "title": "Objeto", "original_text": "Descripción del inmueble"},
            {"contract_type": "arrendamiento_vivienda"},
            legal_context=None
        )

        assert result["clause_result"]["risk_level"] == "none"
        call_args = mock_client.chat.completions.create.call_args
        system_msg = call_args.kwargs["messages"][0]["content"] if "messages" in call_args.kwargs else call_args[1]["messages"][0]["content"]
        assert "prudente" in system_msg.lower()

    @patch('services.legal_analysis.time.sleep')
    @patch('services.legal_analysis.get_openai_client')
    def test_analyze_clause_retry_on_error(self, mock_get_client, mock_sleep):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        ok_response = _openai_chat_response(
            json.dumps({
                "clause_result": {"risk_level": "medium", "has_issue": True,
                                  "plain_explanation": "Problema detectado",
                                  "legal_advice": "Revisar"},
                "risks_to_create": [],
                "positive_aspects_to_create": []
            }), total_tokens=180
        )
        mock_client.chat.completions.create.side_effect = [
            Exception("timeout"), Exception("rate limit"), ok_response
        ]

        from services.legal_analysis import analyze_clause_legal
        result = analyze_clause_legal(
            {"clause_number": "3", "title": "Renta", "original_text": "Renta mensual"},
            {"contract_type": "arrendamiento_vivienda"}
        )

        assert result["clause_result"]["risk_level"] == "medium"
        assert mock_client.chat.completions.create.call_count == 3


@pytest.mark.integration
class TestAggregateAnalysis:

    @patch('services.legal_analysis.get_openai_client')
    def test_aggregate_analysis_risk_levels(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        aggregation = {
            "overall_risk": "medium",
            "summary": "El contrato presenta riesgos moderados.",
            "missing_elements_to_create": []
        }
        mock_client.chat.completions.create.return_value = _openai_chat_response(
            json.dumps(aggregation), total_tokens=300
        )

        from services.legal_analysis import aggregate_analysis
        clause_results = [
            {"clause_number": "1", "risk_level": "none", "has_issue": False, "brief_finding": ""},
            {"clause_number": "2", "risk_level": "high", "has_issue": True, "brief_finding": "Problema"},
            {"clause_number": "3", "risk_level": "low", "has_issue": True, "brief_finding": "Menor"},
        ]
        result = aggregate_analysis(clause_results, {"contract_type": "arrendamiento_vivienda"})

        assert result["overall_risk"] == "medium"
        assert "riesgos" in result["summary"].lower()

    @patch('services.legal_analysis.get_openai_client')
    def test_aggregate_missing_elements(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        aggregation = {
            "overall_risk": "high",
            "summary": "Faltan elementos esenciales.",
            "missing_elements_to_create": [
                {"title": "Fianza", "description": "No se especifica fianza",
                 "suggested_clause": "Añadir cláusula de fianza de 1 mes",
                 "severity": "high", "category": "fianza"}
            ]
        }
        mock_client.chat.completions.create.return_value = _openai_chat_response(
            json.dumps(aggregation), total_tokens=350
        )

        from services.legal_analysis import aggregate_analysis
        result = aggregate_analysis(
            [{"clause_number": "1", "risk_level": "none", "has_issue": False, "brief_finding": ""}],
            {"contract_type": "arrendamiento_vivienda"}
        )

        assert len(result["missing_elements_to_create"]) == 1
        assert result["missing_elements_to_create"][0]["title"] == "Fianza"



@pytest.mark.integration
class TestRAGService:

    @patch('openai.OpenAI')
    @patch('core.config.settings')
    def test_query_embedding_uses_configured_model(self, mock_settings, mock_openai_cls):
        mock_settings.openai_api_key = "sk-test"
        mock_settings.openai_embedding_model = "test-embedding-model"
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.embeddings.create.return_value = _openai_embedding_response([0.1, 0.2])

        from services.rag_service import _get_query_embedding
        result = _get_query_embedding("consulta legal")

        assert result == [0.1, 0.2]
        assert mock_client.embeddings.create.call_args.kwargs == {
            "input": "consulta legal",
            "model": "test-embedding-model",
        }

    @patch('services.rag_service._get_query_embedding', return_value=[0.1] * 1536)
    @patch('services.rag_service._get_qdrant_client')
    @patch('services.rag_service._get_collection_name', return_value="legal_chunks_es_v1_2026_02_14")
    def test_retrieve_legal_context_success(self, mock_coll, mock_qdrant, mock_embed):
        mock_client = MagicMock()
        mock_qdrant.return_value = mock_client

        hit = MagicMock()
        hit.payload = {
            "citation": "Art. 9 LAU",
            "law_name": "LAU 1994",
            "law_key": "LAU_1994",
            "article_number": "9",
            "text": "Duración mínima de 5 años..."
        }
        hit.score = 0.91
        query_result = MagicMock()
        query_result.points = [hit]
        mock_client.query_points.return_value = query_result

        from services.rag_service import retrieve_legal_context
        ctx = retrieve_legal_context("duración del contrato", contract_type="arrendamiento_vivienda")

        assert len(ctx) == 1
        assert ctx[0]["citation"] == "Art. 9 LAU"
        assert ctx[0]["score"] == 0.91

    @patch('services.rag_service._get_query_embedding', return_value=[0.1] * 1536)
    @patch('services.rag_service._get_qdrant_client')
    @patch('services.rag_service._get_collection_name', return_value="legal_chunks_es_v1_2026_02_14")
    def test_retrieve_filter_lau_rental(self, mock_coll, mock_qdrant, mock_embed):
        mock_client = MagicMock()
        mock_qdrant.return_value = mock_client
        query_result = MagicMock()
        query_result.points = []
        mock_client.query_points.return_value = query_result

        from services.rag_service import retrieve_legal_context
        retrieve_legal_context("texto", contract_type="arrendamiento_vivienda")

        call_kwargs = mock_client.query_points.call_args
        qfilter = call_kwargs.kwargs.get("query_filter") or call_kwargs[1].get("query_filter")
        assert qfilter is not None

    @patch('services.rag_service._get_query_embedding', side_effect=Exception("Qdrant down"))
    @patch('services.rag_service._get_collection_name', return_value="test")
    def test_retrieve_graceful_failure(self, mock_coll, mock_embed):
        from services.rag_service import retrieve_legal_context
        result = retrieve_legal_context("texto")
        assert result == []

    @patch('services.rag_service._get_query_embedding', side_effect=Exception("Qdrant down"))
    @patch('services.rag_service._get_collection_name', return_value="test")
    def test_retrieve_strict_failure_raises(self, mock_coll, mock_embed):
        from services.rag_service import retrieve_legal_context
        with pytest.raises(RuntimeError, match="RAG retrieval failed"):
            retrieve_legal_context("texto", strict=True)

    def test_grounded_answer_abstains_without_context(self):
        from services.rag_service import build_grounded_answer
        result = build_grounded_answer([])
        assert result["abstained"] is True
        assert result["citations"] == []
        assert "no se ha encontrado respaldo" in result["answer"].lower()

    def test_grounded_answer_only_uses_retrieved_text(self):
        from services.rag_service import build_grounded_answer
        context = [{"citation": "LAU art. 36", "text": "La fianza será obligatoria."}]
        result = build_grounded_answer(context)
        assert result == {
            "answer": "[LAU art. 36] La fianza será obligatoria.",
            "citations": ["LAU art. 36"],
            "abstained": False,
        }

    def test_collection_name_detection(self):
        with patch('core.config.settings') as mock_s:
            mock_s.qdrant_collection = None
            with patch('services.rag_service.glob') as mock_glob:
                mock_glob.return_value = ["/path/legal_corpus/es/v1_2026-02-14"]
                from services.rag_service import _get_collection_name
                name = _get_collection_name()
                assert "v1_2026_02_14" in name

    def test_format_legal_context(self):
        from services.rag_service import format_legal_context_for_prompt
        context = [
            {"citation": "Art. 10 LAU", "law_name": "LAU 1994",
             "text": "Prórroga del contrato por períodos anuales."},
            {"citation": "Art. 1544 CC", "law_name": "Código Civil",
             "text": "El arrendamiento puede ser de cosas, obras o servicios."},
        ]
        result = format_legal_context_for_prompt(context)

        assert "Art. 10 LAU" in result
        assert "Art. 1544 CC" in result
        assert "CONTEXTO LEGAL" in result

    def test_format_legal_context_empty(self):
        from services.rag_service import format_legal_context_for_prompt
        assert format_legal_context_for_prompt([]) == ""



@pytest.mark.integration
class TestEmailService:

    @pytest.mark.asyncio
    @patch('services.email.email_service.aiosmtplib.SMTP')
    @patch('services.email.email_service.settings')
    async def test_send_password_reset_email(self, mock_settings, mock_smtp_cls):
        mock_settings.smtp_user = "user@test.com"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_from = "noreply@test.com"
        mock_settings.smtp_from_name = "ContratIA"
        mock_settings.frontend_url = "http://localhost:5173"

        mock_smtp = AsyncMock()
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from services.email.email_service import send_password_reset_email
        result = await send_password_reset_email("user@test.com", "Juan", "reset-token-123")

        assert result is True
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.email.email_service.aiosmtplib.SMTP')
    @patch('services.email.email_service.settings')
    async def test_send_welcome_email(self, mock_settings, mock_smtp_cls):
        mock_settings.smtp_user = "user@test.com"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_from = "noreply@test.com"
        mock_settings.smtp_from_name = "ContratIA"

        mock_smtp = AsyncMock()
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        from services.email.email_service import send_welcome_email
        result = await send_welcome_email("new@test.com", "María")

        assert result is True

    @pytest.mark.asyncio
    @patch('services.email.email_service.settings')
    async def test_smtp_not_configured(self, mock_settings):
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""

        from services.email.email_service import send_email
        result = await send_email("to@test.com", "Subject", "<p>Body</p>")

        assert result is False

    @pytest.mark.asyncio
    @patch('services.email.email_service.aiosmtplib.SMTP')
    @patch('services.email.email_service.settings')
    async def test_smtp_connection_error(self, mock_settings, mock_smtp_cls):
        mock_settings.smtp_user = "user@test.com"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_from = "noreply@test.com"
        mock_settings.smtp_from_name = "ContratIA"

        mock_smtp_cls.return_value.__aenter__ = AsyncMock(
            side_effect=ConnectionRefusedError("Connection refused")
        )

        from services.email.email_service import send_email
        result = await send_email("to@test.com", "Subject", "<p>Body</p>")

        assert result is False
