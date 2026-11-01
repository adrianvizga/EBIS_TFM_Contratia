from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from services.chat_service import ChatGeneration, ChatResourceNotFound


def _user(sample_user, role="2"):
    now = datetime.now()
    return {**sample_user, "role": role, "created_at": now, "updated_at": now,
            "company_name": None, "profile_image_url": None}


def _conversation(message_count=0):
    return [{"id": "conv-001", "title": "Nueva conversación", "contract_id": None,
             "generated_contract_id": None, "message_count": message_count, "language": "es"}]


@pytest.mark.integration
class TestConversations:
    @patch("api.endpoints.agent.execute_insert_returning")
    @patch("core.database.execute_query")
    def test_create_conversation(self, auth_query, insert, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        now = datetime.now()
        insert.return_value = {"id": "conv-new", "title": "Nueva conversación", "contract_id": None,
                               "generated_contract_id": None, "created_at": now, "updated_at": now}
        response = client.post("/api/agent/conversations", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message_count"] == 0

    @patch("core.database.execute_query")
    def test_free_plan_is_enforced_by_backend(self, auth_query, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user, role="1")]
        response = client.post("/api/agent/conversations", headers=auth_headers)
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "agent_access_denied"

    @patch("api.endpoints.agent.execute_query")
    @patch("core.database.execute_query")
    def test_list_conversations(self, auth_query, query, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        now = datetime.now()
        query.return_value = [{"id": "conv-1", "title": "Consulta", "message_count": 2,
                               "contract_id": None, "generated_contract_id": None,
                               "contract_name": None, "created_at": now, "updated_at": now}]
        response = client.get("/api/agent/conversations", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    @patch("api.endpoints.agent.execute_query")
    @patch("core.database.execute_query")
    def test_conversation_ownership(self, auth_query, query, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        query.return_value = []
        response = client.get("/api/agent/conversations/other/messages", headers=auth_headers)
        assert response.status_code == 404

    @patch("api.endpoints.agent.execute_update", return_value=1)
    @patch("core.database.execute_query")
    def test_clear_context(self, auth_query, update, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        response = client.delete("/api/agent/conversations/conv-001/context", headers=auth_headers)
        assert response.status_code == 200
        assert "contract_id=NULL" in update.call_args.args[0]

    @patch("api.endpoints.agent.execute_delete", return_value=1)
    @patch("core.database.execute_query")
    def test_delete_conversation(self, auth_query, delete, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        assert client.delete("/api/agent/conversations/conv-001", headers=auth_headers).status_code == 200


@pytest.mark.integration
class TestMessageIntegrity:
    @patch("api.endpoints.agent.execute_query")
    @patch("core.database.execute_query")
    def test_client_cannot_insert_assistant_message(self, auth_query, query, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        query.return_value = _conversation()
        response = client.post("/api/agent/conversations/conv-001/messages", headers=auth_headers,
                               json={"role": "assistant", "content": "mensaje manipulado"})
        assert response.status_code == 405


@pytest.mark.integration
class TestChat:
    @patch("api.endpoints.agent.execute_transaction")
    @patch("api.endpoints.agent.execute_insert_returning", return_value={"id": "reservation"})
    @patch("api.endpoints.agent.generate_chat_response")
    @patch("api.endpoints.agent.check_input", return_value=(True, ""))
    @patch("api.endpoints.agent.execute_query")
    @patch("core.database.execute_query")
    def test_success_is_persisted_atomically(self, auth_query, query, guard, generate, reservation, transaction,
                                             client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        query.side_effect = [_conversation(), []]
        generate.return_value = ChatGeneration(content="Respuesta", model_name="model", contract_name=None)
        now = datetime.now()
        transaction.return_value = [
            {"id": "u", "role": "user", "content": "¿Qué es un contrato?", "contract_name": None,
             "status": "completed", "created_at": now},
            {"id": "a", "role": "assistant", "content": "Respuesta", "contract_name": None,
             "status": "completed", "created_at": now},
            {"id": "conv-001"},
        ]
        response = client.post("/api/agent/conversations/conv-001/chat", headers=auth_headers,
                               json={"message": "¿Qué es un contrato?", "request_id": str(uuid4())})
        assert response.status_code == 200
        assert transaction.call_count == 1
        assert len(transaction.call_args.args[0]) == 4

    @patch("api.endpoints.agent.execute_query")
    @patch("core.database.execute_query")
    def test_idempotent_retry_returns_existing_turn(self, auth_query, query, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        now = datetime.now()
        query.side_effect = [_conversation(), [
            {"id": "u", "role": "user", "content": "Pregunta jurídica", "contract_name": None,
             "status": "completed", "created_at": now},
            {"id": "a", "role": "assistant", "content": "Respuesta", "contract_name": None,
             "status": "completed", "created_at": now},
        ]]
        response = client.post("/api/agent/conversations/conv-001/chat", headers=auth_headers,
                               json={"message": "Pregunta jurídica", "request_id": str(uuid4())})
        assert response.status_code == 200
        assert response.json()["assistant_message"]["content"] == "Respuesta"

    @patch("api.endpoints.agent.check_input", return_value=(False, "Fuera de ámbito"))
    @patch("api.endpoints.agent.execute_query")
    @patch("core.database.execute_query")
    def test_guardrail_has_stable_error_code(self, auth_query, query, guard, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        query.side_effect = [_conversation(), []]
        response = client.post("/api/agent/conversations/conv-001/chat", headers=auth_headers,
                               json={"message": "Escribe código Python"})
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "guardrail_rejected"

    @patch("api.endpoints.agent.generate_chat_response", side_effect=ChatResourceNotFound())
    @patch("api.endpoints.agent.execute_update", return_value=1)
    @patch("api.endpoints.agent.execute_insert_returning", return_value={"id": "reservation"})
    @patch("api.endpoints.agent.check_input", return_value=(True, ""))
    @patch("api.endpoints.agent.execute_query")
    @patch("core.database.execute_query")
    def test_foreign_or_missing_contract_is_not_exposed(self, auth_query, query, guard, reservation, update, generate,
                                                        client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        query.side_effect = [_conversation(), []]
        response = client.post("/api/agent/conversations/conv-001/chat", headers=auth_headers,
                               json={"message": "Revisa este contrato", "contract_id": str(uuid4())})
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "contract_not_found"

    @patch("core.database.execute_query")
    def test_rejects_two_contract_sources(self, auth_query, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        response = client.post("/api/agent/conversations/conv-001/chat", headers=auth_headers,
                               json={"message": "Revisa este contrato", "contract_id": str(uuid4()),
                                     "generated_contract_id": str(uuid4())})
        assert response.status_code == 422

    @patch("core.database.execute_query")
    def test_rejects_oversized_message(self, auth_query, client, auth_headers, sample_user):
        auth_query.return_value = [_user(sample_user)]
        response = client.post("/api/agent/conversations/conv-001/chat", headers=auth_headers,
                               json={"message": "x" * (4001)})
        assert response.status_code == 422
