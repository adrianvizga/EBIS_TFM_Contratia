import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Permite importar el backend al ejecutar estas pruebas directamente.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient
from app import app
from core.security import create_access_token, create_refresh_token, create_reset_token, hash_password


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_headers(sample_user):
    token = create_access_token({"sub": sample_user["id"], "email": sample_user["email"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token({"sub": admin_user["id"], "email": admin_user["email"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def plus_headers(plus_user):
    token = create_access_token({"sub": plus_user["id"], "email": plus_user["email"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pro_headers(pro_user):
    token = create_access_token({"sub": pro_user["id"], "email": pro_user["email"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def registered_user_in_db(sample_user):
    now = datetime.now()
    user = {
        **sample_user,
        'password_hash': hash_password('Test1234'),
        'company_name': None,
        'profile_image_url': None,
        'created_at': now,
        'updated_at': now,
    }
    return user


@pytest.fixture
def mock_get_current_user(sample_user):
    now = datetime.now()
    full_user = {
        **sample_user,
        'company_name': None,
        'profile_image_url': None,
        'created_at': now,
        'updated_at': now,
    }
    with patch('core.security.get_current_user', return_value=full_user) as mock:
        yield mock


@pytest.fixture
def mock_db_full():
    with patch('core.database.execute_query') as eq, \
         patch('core.database.execute_insert') as ei, \
         patch('core.database.execute_insert_returning') as eir, \
         patch('core.database.execute_update') as eu, \
         patch('core.database.execute_delete') as ed, \
         patch('core.database.execute_transaction') as et:
        yield {
            'query': eq,
            'insert': ei,
            'insert_returning': eir,
            'update': eu,
            'delete': ed,
            'transaction': et,
        }
