import uuid

from core import db_initializer


class FakeCursor:
    def __init__(self, existing_user_id=None):
        self.existing_user_id = existing_user_id
        self.queries = []
        self._result = None

    def execute(self, query, params=None):
        self.queries.append((query, params))
        upper_query = query.upper()
        if 'SELECT ID FROM USERS' in upper_query:
            self._result = (
                (self.existing_user_id,) if self.existing_user_id else None
            )
        elif 'INSERT INTO USERS' in upper_query and 'RETURNING ID' in upper_query:
            self._result = (str(uuid.uuid4()),)
        elif 'SELECT ID FROM USER_SETTINGS' in upper_query:
            self._result = None
        else:
            self._result = None

    def fetchone(self):
        result = self._result
        self._result = None
        return result


def test_ensure_demo_user_creates_admin_user_and_settings(mocker):
    cursor = FakeCursor()
    hash_password = mocker.patch.object(
        db_initializer,
        'hash_password',
        return_value='hashed-demo-password',
    )

    user_id = db_initializer._ensure_demo_user(cursor, 'demo')

    assert user_id is not None
    hash_password.assert_called_once_with('demo')

    insert_params = next(
        params
        for query, params in cursor.queries
        if 'INSERT INTO USERS' in query.upper()
    )
    assert insert_params == (
        'demo@ebistfm.com',
        'hashed-demo-password',
        'demo',
        'User',
        'EBIS TFM',
        '0',
    )
    assert any(
        'INSERT INTO USER_SETTINGS' in query.upper()
        for query, _ in cursor.queries
    )


def test_ensure_demo_user_preserves_existing_profile_and_password(mocker):
    existing_id = str(uuid.uuid4())
    cursor = FakeCursor(existing_user_id=existing_id)
    hash_password = mocker.patch.object(db_initializer, 'hash_password')

    user_id = db_initializer._ensure_demo_user(cursor, 'demo')

    assert user_id == existing_id
    hash_password.assert_not_called()
    update_query, update_params = next(
        (query, params)
        for query, params in cursor.queries
        if 'UPDATE USERS' in query.upper()
    )
    assert 'PASSWORD_HASH' not in update_query.upper()
    assert 'FIRST_NAME' not in update_query.upper()
    assert update_params == ('0', 'demo@ebistfm.com')


def test_prepare_demo_user_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv('DEMO_USER_ENABLED', raising=False)
    cursor = FakeCursor()

    db_initializer._prepare_demo_user(cursor)

    assert cursor.queries == []


def test_prepare_demo_user_uses_configured_password(monkeypatch, mocker):
    monkeypatch.setenv('DEMO_USER_ENABLED', 'true')
    monkeypatch.setenv('DEMO_USER_PASSWORD', 'local-test-password')
    ensure_demo_user = mocker.patch.object(
        db_initializer,
        '_ensure_demo_user',
        return_value='demo-id',
    )
    cursor = FakeCursor()

    db_initializer._prepare_demo_user(cursor)

    ensure_demo_user.assert_called_once_with(cursor, 'local-test-password')
