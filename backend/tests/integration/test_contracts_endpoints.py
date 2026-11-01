import pytest
import io
from unittest.mock import patch, MagicMock
from datetime import datetime


# Funciones auxiliares

def _make_upload_file(name="test.pdf", content=b"%PDF-1.4 fake content", content_type="application/pdf"):
    return (name, io.BytesIO(content), content_type)


# POST /api/contracts/upload

@pytest.mark.integration
class TestUploadContract:

    @patch('api.endpoints.contracts.create_notification')
    @patch('api.endpoints.contracts.reserve_contract_analysis', return_value=True)
    @patch('api.endpoints.contracts.enqueue_contract_analysis')
    @patch('api.endpoints.contracts.execute_transaction')
    @patch('api.endpoints.contracts.can_analyze_contract', return_value=True)
    @patch('core.database.execute_query')
    def test_upload_pdf_success(self, mock_eq, mock_can, mock_transaction, mock_enqueue, mock_incr, mock_notif,
                                 client, auth_headers, sample_user, tmp_path):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq.return_value = [full_user]
        mock_transaction.return_value = [{'id': 'contract-123'}, {'id': 'analysis-123'}]
        mock_enqueue.return_value = 'task-123'

        resp = client.post(
            "/api/contracts/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.pdf"
        assert data["status"] == "pending"

    @patch('api.endpoints.contracts.can_analyze_contract', return_value=True)
    @patch('api.endpoints.contracts.execute_transaction')
    @patch('api.endpoints.contracts.enqueue_contract_analysis')
    @patch('api.endpoints.contracts.reserve_contract_analysis', return_value=True)
    @patch('core.database.execute_query')
    def test_upload_txt_success(self, mock_eq, mock_incr, mock_enqueue, mock_transaction, mock_can,
                                 client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq.return_value = [full_user]
        mock_transaction.return_value = [{'id': 'contract-txt'}, {'id': 'analysis-txt'}]
        mock_enqueue.return_value = 'task-txt'

        resp = client.post(
            "/api/contracts/upload",
            headers=auth_headers,
            files={"file": ("test.txt", io.BytesIO(b"Contrato de prueba"), "text/plain")},
        )

        assert resp.status_code == 200

    @patch('api.endpoints.contracts.can_analyze_contract', return_value=True)
    @patch('core.database.execute_query')
    def test_upload_invalid_type(self, mock_eq, mock_can, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq.return_value = [full_user]

        resp = client.post(
            "/api/contracts/upload",
            headers=auth_headers,
            files={"file": ("virus.exe", io.BytesIO(b"MZ\x00"), "application/octet-stream")},
        )

        assert resp.status_code == 400

    @patch('api.endpoints.contracts.can_analyze_contract', return_value=True)
    @patch('core.database.execute_query')
    def test_upload_rejects_empty_file(self, mock_eq, mock_can, client, auth_headers, sample_user):
        mock_eq.return_value = [{**sample_user, 'created_at': datetime.now(), 'updated_at': datetime.now()}]
        resp = client.post(
            "/api/contracts/upload", headers=auth_headers,
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert resp.status_code == 400

    @patch('api.endpoints.contracts.can_analyze_contract', return_value=True)
    @patch('core.database.execute_query')
    def test_upload_rejects_forged_pdf(self, mock_eq, mock_can, client, auth_headers, sample_user):
        mock_eq.return_value = [{**sample_user, 'created_at': datetime.now(), 'updated_at': datetime.now()}]
        resp = client.post(
            "/api/contracts/upload", headers=auth_headers,
            files={"file": ("fake.pdf", io.BytesIO(b"not a pdf"), "application/pdf")},
        )
        assert resp.status_code == 400

    @patch('api.endpoints.contracts.can_analyze_contract', return_value=True)
    @patch('core.database.execute_query')
    def test_upload_rejects_legacy_doc(self, mock_eq, mock_can, client, auth_headers, sample_user):
        mock_eq.return_value = [{**sample_user, 'created_at': datetime.now(), 'updated_at': datetime.now()}]
        resp = client.post(
            "/api/contracts/upload", headers=auth_headers,
            files={"file": ("legacy.doc", io.BytesIO(b"legacy"), "application/msword")},
        )
        assert resp.status_code == 400

    @patch('api.endpoints.contracts.can_analyze_contract', return_value=True)
    @patch('core.database.execute_query')
    def test_upload_too_large(self, mock_eq, mock_can, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq.return_value = [full_user]

        large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        resp = client.post(
            "/api/contracts/upload",
            headers=auth_headers,
            files={"file": ("big.pdf", io.BytesIO(large_content), "application/pdf")},
        )

        assert resp.status_code == 400

    @patch('api.endpoints.contracts.can_analyze_contract', return_value=False)
    @patch('core.database.execute_query')
    def test_upload_usage_limit_reached(self, mock_eq, mock_can, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq.return_value = [full_user]

        resp = client.post(
            "/api/contracts/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )

        assert resp.status_code == 403

    @patch('api.endpoints.contracts.create_notification')
    @patch('api.endpoints.contracts.reserve_contract_analysis', return_value=True)
    @patch('api.endpoints.contracts.enqueue_contract_analysis')
    @patch('api.endpoints.contracts.execute_transaction')
    @patch('api.endpoints.contracts.can_analyze_contract', return_value=True)
    @patch('core.database.execute_query')
    def test_upload_triggers_celery(self, mock_eq, mock_can, mock_transaction, mock_enqueue, mock_incr, mock_notif,
                                     client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq.return_value = [full_user]
        mock_transaction.return_value = [{'id': 'contract-celery'}, {'id': 'analysis-celery'}]
        mock_enqueue.return_value = 'task-celery'

        client.post(
            "/api/contracts/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )

        mock_enqueue.assert_called_once()


# GET /api/contracts


@pytest.mark.integration
class TestRetryContractAnalysis:
    @patch('api.endpoints.contracts.enqueue_contract_analysis', return_value='task-retry')
    @patch('api.endpoints.contracts.execute_transaction')
    @patch('api.endpoints.contracts.execute_query')
    @patch('core.database.execute_query')
    def test_retry_failed_contract(self, mock_auth_query, mock_query, mock_transaction, mock_enqueue,
                                   client, auth_headers, sample_user):
        mock_auth_query.return_value = [{**sample_user, 'created_at': datetime.now(), 'updated_at': datetime.now()}]
        mock_query.return_value = [{'id': 'contract-1', 'status': 'error'}]

        response = client.post('/api/contracts/contract-1/retry', headers=auth_headers)

        assert response.status_code == 200
        assert response.json()['status'] == 'pending'
        mock_transaction.assert_called_once()
        mock_enqueue.assert_called_once_with('contract-1')

    @patch('api.endpoints.contracts.execute_query')
    @patch('core.database.execute_query')
    def test_retry_rejects_completed_contract(self, mock_auth_query, mock_query,
                                              client, auth_headers, sample_user):
        mock_auth_query.return_value = [{**sample_user, 'created_at': datetime.now(), 'updated_at': datetime.now()}]
        mock_query.return_value = [{'id': 'contract-1', 'status': 'completed'}]

        response = client.post('/api/contracts/contract-1/retry', headers=auth_headers)

        assert response.status_code == 409

@pytest.mark.integration
class TestListContracts:

    @patch('api.endpoints.contracts.execute_query')
    @patch('core.database.execute_query')
    def test_list_contracts(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq_auth.return_value = [full_user]
        mock_eq_endpoint.return_value = [
            {
                'id': 'c1', 'file_name': 'contrato.pdf', 'created_at': now,
                'status': 'completed', 'error_message': None,
                'risk_count': 2, 'positive_count': 3, 'max_risk_level': 'medium',
            },
        ]

        resp = client.get("/api/contracts", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["filename"] == "contrato.pdf"

    @patch('api.endpoints.contracts.execute_query')
    @patch('core.database.execute_query')
    def test_list_contracts_empty(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq_auth.return_value = [full_user]
        mock_eq_endpoint.return_value = []

        resp = client.get("/api/contracts", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json() == []


# GET /api/contracts/{contract_id}/analysis

@pytest.mark.integration
class TestGetAnalysis:

    @patch('api.endpoints.contracts.execute_query')
    @patch('core.database.execute_query')
    def test_get_analysis_success(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq_auth.return_value = [full_user]

        mock_eq_endpoint.side_effect = [
            [{'id': 'c1', 'original_file_name': 'test.pdf', 'uploaded_at': now,
              'status': 'completed', 'overall_risk': 'medium', 'contract_type': 'Arrendamiento',
              'page_count': 5}],
            [{'id': 'a1', 'status': 'completed', 'overall_risk': 'medium'}],
            [{'id': 'cl1', 'clause_number': '1', 'title': 'Objeto',
              'original_text': 'Texto...', 'plain_explanation': 'Simple',
              'legal_advice': None, 'risk_level': 'none'}],
            [{'title': 'Riesgo', 'severity': 'high'}],
            [{'title': 'Positivo'}],
            [{'title': 'Ausente', 'severity': 'medium'}],
            [],
            [],
        ]

        resp = client.get("/api/contracts/c1/analysis", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.pdf"
        assert len(data["clauses"]) == 1
        assert data["riskCount"] == 1

    @patch('api.endpoints.contracts.execute_query')
    @patch('core.database.execute_query')
    def test_get_analysis_other_user(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq_auth.return_value = [full_user]
        mock_eq_endpoint.return_value = []  # no pertenece al usuario

        resp = client.get("/api/contracts/other-contract/analysis", headers=auth_headers)

        assert resp.status_code == 404

    @patch('api.endpoints.contracts.execute_query')
    @patch('core.database.execute_query')
    def test_get_analysis_not_found(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq_auth.return_value = [full_user]
        mock_eq_endpoint.return_value = []

        resp = client.get("/api/contracts/nonexistent/analysis", headers=auth_headers)

        assert resp.status_code == 404


# DELETE /api/contracts/{contract_id}

@pytest.mark.integration
class TestDeleteContract:

    @patch('api.endpoints.contracts.execute_delete')
    @patch('api.endpoints.contracts.execute_query')
    @patch('core.database.execute_query')
    def test_delete_contract_success(self, mock_eq_auth, mock_eq_endpoint, mock_del,
                                      client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq_auth.return_value = [full_user]
        mock_eq_endpoint.return_value = [{'id': 'c1'}]  # pertenece al usuario
        mock_del.return_value = 1

        resp = client.delete("/api/contracts/c1", headers=auth_headers)

        assert resp.status_code == 200

    @patch('api.endpoints.contracts.execute_query')
    @patch('core.database.execute_query')
    def test_delete_contract_other_user(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        now = datetime.now()
        full_user = {**sample_user, 'company_name': None, 'profile_image_url': None,
                     'created_at': now, 'updated_at': now}
        mock_eq_auth.return_value = [full_user]
        mock_eq_endpoint.return_value = []  # no encontrado para este usuario

        resp = client.delete("/api/contracts/not-mine", headers=auth_headers)

        assert resp.status_code == 404
