
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_db():
    with patch('core.database.execute_query') as eq, \
         patch('core.database.execute_insert') as ei, \
         patch('core.database.execute_update') as eu, \
         patch('core.database.execute_delete') as ed:
        yield {'query': eq, 'insert': ei, 'update': eu, 'delete': ed}


@pytest.fixture
def sample_user():
    return {
        'id': 'usr-test-001',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'role': '1',
        'is_active': True,
        'profile_image': None,
        'auth_provider': 'email'
    }


@pytest.fixture
def admin_user(sample_user):
    return {**sample_user, 'id': 'usr-admin-001', 'role': '0'}


@pytest.fixture
def plus_user(sample_user):
    return {**sample_user, 'id': 'usr-plus-001', 'role': '2'}


@pytest.fixture
def pro_user(sample_user):
    return {**sample_user, 'id': 'usr-pro-001', 'role': '3'}
