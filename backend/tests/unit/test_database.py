import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from core.database import parse_db_url

pytestmark = pytest.mark.unit


class TestParseDbUrl:

    def test_parse_url_standard(self):
        result = parse_db_url("postgresql://user:pass@host:5432/db")
        assert result == {
            "user": "user",
            "password": "pass",
            "host": "host",
            "port": 5432,
            "database": "db",
        }

    def test_parse_url_custom_port(self):
        result = parse_db_url("postgresql://user:pass@host:5433/db")
        assert result["port"] == 5433

    def test_parse_url_complex_password(self):
        result = parse_db_url("postgresql://admin:p%40ssw0rd@host:5432/mydb")
        assert result["password"] == "p%40ssw0rd"
        assert result["user"] == "admin"

    def test_parse_url_no_port_raises(self):
        with pytest.raises(ValueError):
            parse_db_url("postgresql://user:pass@host/db")

    def test_parse_url_invalid_format(self):
        with pytest.raises(ValueError):
            parse_db_url("not-a-database-url")


class TestExecuteQuery:

    @patch("core.database._init_pool")
    def test_execute_query_returns_list_of_dicts(self, mock_pool):
        from core.database import execute_query

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": "1", "name": "test"},
            {"id": "2", "name": "test2"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.return_value = MagicMock()
        mock_pool.return_value.getconn.return_value = mock_conn

        result = execute_query("SELECT * FROM test")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "1"


class TestExecuteInsert:

    @patch("core.database._init_pool")
    def test_execute_insert_commits(self, mock_pool):
        from core.database import execute_insert

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": "new-1"}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.return_value = MagicMock()
        mock_pool.return_value.getconn.return_value = mock_conn

        result = execute_insert("INSERT INTO test VALUES (1) RETURNING id")
        mock_conn.commit.assert_called_once()
        assert result["id"] == "new-1"


class TestExecuteUpdate:

    @patch("core.database._init_pool")
    def test_execute_update_returns_rowcount(self, mock_pool):
        from core.database import execute_update

        mock_cursor = MagicMock()
        mock_cursor.rowcount = 3
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.return_value = MagicMock()
        mock_pool.return_value.getconn.return_value = mock_conn

        result = execute_update("UPDATE test SET x=1")
        assert result == 3
        mock_conn.commit.assert_called_once()


class TestExecuteDelete:

    @patch("core.database._init_pool")
    def test_execute_delete_returns_rowcount(self, mock_pool):
        from core.database import execute_delete

        mock_cursor = MagicMock()
        mock_cursor.rowcount = 2
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.return_value = MagicMock()
        mock_pool.return_value.getconn.return_value = mock_conn

        result = execute_delete("DELETE FROM test WHERE id=1")
        assert result == 2
        mock_conn.commit.assert_called_once()


class TestExecuteTransaction:

    @patch("core.database._init_pool")
    def test_transaction_commits_all(self, mock_pool):
        from core.database import execute_transaction

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [{"id": "1"}, None]
        mock_cursor.rowcount = 1
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.return_value = MagicMock()
        mock_pool.return_value.getconn.return_value = mock_conn

        ops = [
            ("INSERT INTO t1 VALUES (1) RETURNING id", {}),
            ("UPDATE t2 SET x=1", {}),
        ]
        execute_transaction(ops)
        mock_conn.commit.assert_called_once()

    @patch("core.database._init_pool")
    def test_transaction_rollback_on_error(self, mock_pool):
        from core.database import execute_transaction

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = [None, Exception("DB error")]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.return_value = MagicMock()
        mock_pool.return_value.getconn.return_value = mock_conn

        with pytest.raises(Exception, match="DB error"):
            execute_transaction([
                ("SELECT 1", {}),
                ("INVALID QUERY", {}),
                ("SELECT 2", {}),
            ])
        mock_conn.rollback.assert_called_once()
