import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime



def _gen_contract_row(overrides=None):
    now = datetime.now()
    base = {
        'id': 'gc-001', 'title': 'Contrato de prueba',
        'contract_type': 'Arrendamiento', 'country': 'España',
        'language': 'Español', 'tone': 'Legal Formal',
        'status': 'completed', 'current_content': 'Contenido del contrato...',
        'contract_details': None,
        'created_at': now, 'updated_at': now,
    }
    if overrides:
        base.update(overrides)
    return base


def _full_user(sample_user):
    now = datetime.now()
    return {
        **sample_user,
        'company_name': None, 'profile_image_url': None,
        'created_at': now, 'updated_at': now,
    }



@pytest.mark.integration
class TestCreateGeneratedContract:

    @patch('workers.tasks.generate_contract_task')
    @patch('api.endpoints.generated_contracts.generate_contract_task', create=True)
    @patch('core.database.release_connection')
    @patch('core.database.get_connection')
    @patch('api.endpoints.generated_contracts.can_generate_contract', return_value=True)
    @patch('api.endpoints.generated_contracts.check_input', return_value=(True, None))
    @patch('core.database.execute_query')
    def test_create_success(self, mock_eq, mock_guard, mock_can, mock_get_conn,
                             mock_release, mock_task, mock_task_worker, client, auth_headers, sample_user):
        mock_eq.return_value = [_full_user(sample_user)]

        mock_cursor = MagicMock()
        now = datetime.now()
        mock_cursor.fetchone.return_value = _gen_contract_row({'status': 'pending', 'current_content': ''})
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_task.delay = MagicMock()

        resp = client.post("/api/generated-contracts", headers=auth_headers, json={
            "title": "Contrato test",
            "contract_type": "Arrendamiento",
        })

        assert resp.status_code == 200

    @patch('api.endpoints.generated_contracts.can_generate_contract', return_value=True)
    @patch('api.endpoints.generated_contracts.check_input', return_value=(False, "Contenido no permitido"))
    @patch('core.database.execute_query')
    def test_create_guardrail_block(self, mock_eq, mock_guard, mock_can,
                                     client, auth_headers, sample_user):
        mock_eq.return_value = [_full_user(sample_user)]

        resp = client.post("/api/generated-contracts", headers=auth_headers, json={
            "title": "Receta de cocina",
            "contract_type": "General",
        })

        assert resp.status_code == 422

    @patch('api.endpoints.generated_contracts.check_input', return_value=(True, None))
    @patch('api.endpoints.generated_contracts.can_generate_contract', return_value=False)
    @patch('core.database.execute_query')
    def test_create_usage_limit(self, mock_eq, mock_can, mock_guard,
                                 client, auth_headers, sample_user):
        mock_eq.return_value = [_full_user(sample_user)]

        resp = client.post("/api/generated-contracts", headers=auth_headers, json={
            "title": "Contrato",
            "contract_type": "Arrendamiento",
        })

        assert resp.status_code == 403



@pytest.mark.integration
class TestListGeneratedContracts:

    @patch('api.endpoints.generated_contracts.execute_query')
    @patch('core.database.execute_query')
    def test_list_all(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = [_gen_contract_row()]

        resp = client.get("/api/generated-contracts", headers=auth_headers)

        assert resp.status_code == 200
        assert len(resp.json()) == 1



@pytest.mark.integration
class TestGetGeneratedContract:

    @patch('api.endpoints.generated_contracts.execute_query')
    @patch('core.database.execute_query')
    def test_get_by_id(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = [_gen_contract_row()]

        resp = client.get("/api/generated-contracts/gc-001", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["title"] == "Contrato de prueba"

    @patch('api.endpoints.generated_contracts.execute_query')
    @patch('core.database.execute_query')
    def test_get_other_user(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = []

        resp = client.get("/api/generated-contracts/other-gc", headers=auth_headers)

        assert resp.status_code == 404



@pytest.mark.integration
class TestUpdateGeneratedContract:

    @patch('services.generated_contracts_repository.save_version')
    @patch('api.endpoints.generated_contracts.execute_insert_returning')
    @patch('api.endpoints.generated_contracts.execute_query')
    @patch('core.database.execute_query')
    def test_update_manual(self, mock_eq_auth, mock_eq_endpoint, mock_insert_ret, mock_save,
                            client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.side_effect = [
            [{'id': 'gc-001'}],
            [{'max_ver': 1}],
        ]
        now = datetime.now()
        valid_content = "CLÁUSULA PRIMERA. OBJETO\n" + ("Contenido contractual válido. " * 20)
        mock_save.return_value = _gen_contract_row({'current_content': valid_content})

        resp = client.put("/api/generated-contracts/gc-001", headers=auth_headers, json={
            "content": valid_content,
            "change_type": "Manual",
        })

        assert resp.status_code == 200



@pytest.mark.integration
class TestAIModification:

    @patch('services.generated_contracts_repository.save_version')
    @patch('api.endpoints.generated_contracts.create_notification')
    @patch('api.endpoints.generated_contracts.increment_ai_modifications')
    @patch('api.endpoints.generated_contracts.execute_insert_returning')
    @patch('api.endpoints.generated_contracts.execute_query')
    @patch('api.endpoints.generated_contracts.can_modify_with_ai', return_value=True)
    @patch('api.endpoints.generated_contracts.check_input', return_value=(True, None))
    @patch('services.openai_client.modify_contract_content')
    @patch('api.endpoints.generated_contracts.modify_contract_content', create=True)
    @patch('core.database.execute_query')
    def test_ai_modification_success(self, mock_eq_auth, mock_modify_mod, mock_modify, mock_guard, mock_can,
                                       mock_eq_endpoint, mock_insert_ret, mock_incr, mock_notif, mock_save,
                                       client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.side_effect = [
            [_gen_contract_row()],
            [{'max_ver': 1}],
        ]
        valid_content = "CONTRATO DE ARRENDAMIENTO\nCLÁUSULA PRIMERA. RENTA, DURACIÓN Y FIANZA.\n" + ("Obligaciones y condiciones del arrendamiento. " * 15) + "\nFIRMAS"
        mock_modify.return_value = valid_content
        mock_save.return_value = _gen_contract_row({'current_content': valid_content})
        now = datetime.now()
        mock_insert_ret.side_effect = [
            _gen_contract_row({'current_content': 'Contenido modificado por IA'}),
            {'id': 'v2'},
        ]

        resp = client.post("/api/generated-contracts/gc-001/generate", headers=auth_headers, json={
            "prompt": "Añade una cláusula de penalización",
        })

        assert resp.status_code == 200

    @patch('api.endpoints.generated_contracts.can_modify_with_ai', return_value=True)
    @patch('api.endpoints.generated_contracts.check_input', return_value=(False, "Contenido bloqueado"))
    @patch('core.database.execute_query')
    def test_ai_modification_guardrail(self, mock_eq_auth, mock_guard, mock_can,
                                        client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]

        resp = client.post("/api/generated-contracts/gc-001/generate", headers=auth_headers, json={
            "prompt": "Escribe un poema",
        })

        assert resp.status_code == 422

    @patch('api.endpoints.generated_contracts.check_input', return_value=(True, None))
    @patch('api.endpoints.generated_contracts.can_modify_with_ai', return_value=False)
    @patch('core.database.execute_query')
    def test_ai_modification_limit(self, mock_eq_auth, mock_can, mock_guard,
                                    client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]

        resp = client.post("/api/generated-contracts/gc-001/generate", headers=auth_headers, json={
            "prompt": "Añade cláusula",
        })

        assert resp.status_code == 403



@pytest.mark.integration
class TestDeleteGeneratedContract:

    @patch('api.endpoints.generated_contracts.execute_update')
    @patch('api.endpoints.generated_contracts.execute_query')
    @patch('core.database.execute_query')
    def test_delete_success(self, mock_eq_auth, mock_eq_endpoint, mock_upd,
                             client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = [{'id': 'gc-001'}]
        mock_upd.return_value = 1

        resp = client.delete("/api/generated-contracts/gc-001", headers=auth_headers)

        assert resp.status_code == 200



@pytest.mark.integration
class TestSendToAnalysis:

    @patch('api.endpoints.generated_contracts.create_notification')
    @patch('api.endpoints.generated_contracts.increment_contracts_analyzed')
    @patch('api.endpoints.generated_contracts.enqueue_contract_analysis')
    @patch('api.endpoints.generated_contracts.execute_insert_returning')
    @patch('api.endpoints.generated_contracts.execute_query')
    @patch('api.endpoints.generated_contracts.can_analyze_contract', return_value=True)
    @patch('core.database.execute_query')
    def test_send_to_analysis(self, mock_eq_auth, mock_can, mock_eq_endpoint,
                               mock_insert_ret, mock_enqueue, mock_incr, mock_notif,
                               client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = [
            _gen_contract_row({'current_content': 'Contenido válido'}),
        ]
        mock_insert_ret.side_effect = [
            {'id': 'new-contract-id'},
            {'id': 'analysis-id'},
        ]

        resp = client.post("/api/generated-contracts/gc-001/send-to-analysis", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        mock_enqueue.assert_called_once()

    @patch('api.endpoints.generated_contracts.can_analyze_contract', return_value=False)
    @patch('core.database.execute_query')
    def test_send_to_analysis_limit(self, mock_eq_auth, mock_can,
                                     client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]

        resp = client.post("/api/generated-contracts/gc-001/send-to-analysis", headers=auth_headers)

        assert resp.status_code == 403
