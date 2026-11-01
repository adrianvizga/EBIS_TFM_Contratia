import pytest
from unittest.mock import MagicMock, patch, call

pytestmark = pytest.mark.unit


def _make_conn(cursor_fetchone_values=None, fetchone_seq=None):
    """Return a mocked psycopg2 connection whose cursor.fetchone() returns given values."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    if fetchone_seq is not None:
        mock_cursor.fetchone.side_effect = fetchone_seq
    elif cursor_fetchone_values is not None:
        mock_cursor.fetchone.return_value = cursor_fetchone_values
    return mock_conn, mock_cursor


@pytest.fixture(autouse=True)
def patch_psycopg2_real_dict_cursor():
    with patch("psycopg2.extras.RealDictCursor") as cls:
        yield cls


class TestSaveVersion:

    def test_save_version_success(self):
        contract_row = {"id": "c1"}
        version_row = {"next_ver": 2}
        updated_row = {
            "id": "c1", "title": "T", "contract_type": "A", "country": "ES",
            "language": "es", "tone": "formal", "status": "completed",
            "current_content": "nuevo", "contract_details": {}, "error_message": None,
            "generation_prompt_version": "v1", "model_name": "m",
            "created_at": None, "updated_at": None,
        }
        mock_conn, mock_cursor = _make_conn(fetchone_seq=[contract_row, version_row, updated_row])

        with patch("services.generated_contracts_repository.get_connection", return_value=mock_conn), \
             patch("services.generated_contracts_repository.release_connection") as mock_release:
            from services.generated_contracts_repository import save_version
            result = save_version("c1", "nuevo", "manual", "Edición manual")

        mock_conn.commit.assert_called_once()
        mock_release.assert_called_once_with(mock_conn)
        assert result["id"] == "c1"

    def test_save_version_contract_not_found(self):
        mock_conn, mock_cursor = _make_conn(fetchone_seq=[None])

        with patch("services.generated_contracts_repository.get_connection", return_value=mock_conn), \
             patch("services.generated_contracts_repository.release_connection") as mock_release:
            from services.generated_contracts_repository import save_version
            with pytest.raises(LookupError, match="Contract not found"):
                save_version("missing", "content", "manual", "desc")

        mock_conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(mock_conn)

    def test_save_version_db_error_triggers_rollback(self):
        mock_conn, mock_cursor = _make_conn()
        mock_cursor.execute.side_effect = Exception("DB error")

        with patch("services.generated_contracts_repository.get_connection", return_value=mock_conn), \
             patch("services.generated_contracts_repository.release_connection") as mock_release:
            from services.generated_contracts_repository import save_version
            with pytest.raises(Exception, match="DB error"):
                save_version("c1", "content", "manual", "desc")

        mock_conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(mock_conn)


class TestCompleteGeneration:

    def _updated_row(self):
        return {
            "id": "c1", "title": "T", "contract_type": "A", "country": "ES",
            "language": "es", "tone": "formal", "status": "completed",
            "current_content": "generado", "contract_details": {}, "error_message": None,
            "generation_prompt_version": "v2", "model_name": "m",
            "created_at": None, "updated_at": None,
        }

    def test_complete_generation_success(self):
        status_row = {"status": "pending", "user_id": "u1"}
        mock_conn, mock_cursor = _make_conn(fetchone_seq=[status_row, self._updated_row()])

        with patch("services.generated_contracts_repository.get_connection", return_value=mock_conn), \
             patch("services.generated_contracts_repository.release_connection") as mock_release:
            from services.generated_contracts_repository import complete_generation
            result, completed = complete_generation("c1", "generado", "v2", "model-x")

        assert completed is True
        assert result["status"] == "completed"
        mock_conn.commit.assert_called_once()
        mock_release.assert_called_once_with(mock_conn)

    def test_complete_generation_already_completed_returns_false(self):
        status_row = {"status": "completed", "user_id": "u1"}
        mock_conn, mock_cursor = _make_conn(fetchone_seq=[status_row])

        with patch("services.generated_contracts_repository.get_connection", return_value=mock_conn), \
             patch("services.generated_contracts_repository.release_connection") as mock_release:
            from services.generated_contracts_repository import complete_generation
            result, completed = complete_generation("c1", "content", "v2", "model-x")

        assert completed is False
        assert result == {}
        mock_conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(mock_conn)

    def test_complete_generation_contract_not_found(self):
        mock_conn, mock_cursor = _make_conn(fetchone_seq=[None])

        with patch("services.generated_contracts_repository.get_connection", return_value=mock_conn), \
             patch("services.generated_contracts_repository.release_connection") as mock_release:
            from services.generated_contracts_repository import complete_generation
            with pytest.raises(LookupError, match="Contract not found"):
                complete_generation("missing", "content", "v2", "model-x")

        mock_conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(mock_conn)

    def test_complete_generation_db_error_triggers_rollback(self):
        mock_conn, mock_cursor = _make_conn()
        mock_cursor.execute.side_effect = Exception("DB failure")

        with patch("services.generated_contracts_repository.get_connection", return_value=mock_conn), \
             patch("services.generated_contracts_repository.release_connection") as mock_release:
            from services.generated_contracts_repository import complete_generation
            with pytest.raises(Exception, match="DB failure"):
                complete_generation("c1", "content", "v2", "model-x")

        mock_conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(mock_conn)
