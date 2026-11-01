import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# Funciones auxiliares

def _full_user(sample_user):
    now = datetime.now()
    return {
        **sample_user,
        'company_name': None, 'profile_image_url': None,
        'created_at': now, 'updated_at': now,
    }


def _notif_row(overrides=None):
    now = datetime.now()
    base = {
        'id': 'notif-001',
        'user_id': 'usr-test-001',
        'title': 'Test notification',
        'message': 'Body message',
        'notification_type': 'info',
        'is_read': False,
        'related_entity_type': None,
        'related_entity_id': None,
        'created_at': now,
        'updated_at': now,
    }
    if overrides:
        base.update(overrides)
    return base


# POST /api/notifications

@pytest.mark.integration
class TestCreateNotification:

    @patch('api.endpoints.notifications.create_notification', return_value=True)
    @patch('core.database.execute_query')
    def test_create_notification(self, mock_eq, mock_create, client, auth_headers, sample_user):
        mock_eq.return_value = [_full_user(sample_user)]

        resp = client.post("/api/notifications", headers=auth_headers, json={
            "title": "Nueva alerta",
            "message": "Tu contrato fue analizado",
            "notification_type": "success",
        })

        assert resp.status_code == 200
        mock_create.assert_called_once()


# GET /api/notifications

@pytest.mark.integration
class TestListNotifications:

    @patch('api.endpoints.notifications.execute_query')
    @patch('core.database.execute_query')
    def test_list_paginated(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = [_notif_row(), _notif_row({'id': 'notif-002'})]

        resp = client.get("/api/notifications?limit=10&skip=0", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @patch('api.endpoints.notifications.execute_query')
    @patch('core.database.execute_query')
    def test_only_own_notifications(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = []

        resp = client.get("/api/notifications", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json() == []


# GET /api/notifications/unread-count

@pytest.mark.integration
class TestUnreadCount:

    @patch('api.endpoints.notifications.execute_query')
    @patch('core.database.execute_query')
    def test_unread_count(self, mock_eq_auth, mock_eq_endpoint, client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = [{'count': 7}]

        resp = client.get("/api/notifications/unread-count", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["unread_count"] == 7


# PUT /api/notifications/{id}/read

@pytest.mark.integration
class TestMarkSingleRead:

    @patch('api.endpoints.notifications.execute_update')
    @patch('api.endpoints.notifications.execute_query')
    @patch('core.database.execute_query')
    def test_mark_single_read(self, mock_eq_auth, mock_eq_endpoint, mock_upd,
                                client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = [{'id': 'notif-001'}]  # pertenece al usuario
        mock_upd.return_value = 1

        resp = client.put("/api/notifications/notif-001/read", headers=auth_headers)

        assert resp.status_code == 200
        mock_upd.assert_called_once()


# PUT /api/notifications/mark-all-read

@pytest.mark.integration
class TestMarkAllRead:

    @patch('api.endpoints.notifications.execute_update')
    @patch('core.database.execute_query')
    def test_mark_all_read(self, mock_eq, mock_upd, client, auth_headers, sample_user):
        mock_eq.return_value = [_full_user(sample_user)]
        mock_upd.return_value = 5

        resp = client.put("/api/notifications/mark-all-read", headers=auth_headers)

        assert resp.status_code == 200
        mock_upd.assert_called_once()


# DELETE /api/notifications/{id}

@pytest.mark.integration
class TestDeleteSingle:

    @patch('api.endpoints.notifications.execute_update')
    @patch('api.endpoints.notifications.execute_query')
    @patch('core.database.execute_query')
    def test_delete_single(self, mock_eq_auth, mock_eq_endpoint, mock_upd,
                            client, auth_headers, sample_user):
        mock_eq_auth.return_value = [_full_user(sample_user)]
        mock_eq_endpoint.return_value = [{'id': 'notif-001'}]
        mock_upd.return_value = 1

        resp = client.delete("/api/notifications/notif-001", headers=auth_headers)

        assert resp.status_code == 200


# DELETE /api/notifications/delete-all

@pytest.mark.integration
class TestDeleteAll:

    @patch('api.endpoints.notifications.execute_update')
    @patch('core.database.execute_query')
    def test_delete_all(self, mock_eq, mock_upd, client, auth_headers, sample_user):
        mock_eq.return_value = [_full_user(sample_user)]
        mock_upd.return_value = 10

        resp = client.delete("/api/notifications/delete-all", headers=auth_headers)

        assert resp.status_code == 200
        mock_upd.assert_called_once()
