
from typing import Any
from datetime import date
import psycopg2.extras

from core.database import get_connection, release_connection

CONTRACT_COLUMNS = """id::text, title, contract_type, country, language, tone, status,
current_content, contract_details, error_message, generation_prompt_version, model_name,
created_at, updated_at"""


def save_version(contract_id: str, content: str, change_type: str, description: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id FROM generated_contracts WHERE id = %(id)s FOR UPDATE", {"id": contract_id})
        if not cursor.fetchone():
            raise LookupError("Contract not found")
        cursor.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_ver FROM generated_contract_versions WHERE contract_id = %(id)s",
            {"id": contract_id},
        )
        next_ver = cursor.fetchone()["next_ver"]
        cursor.execute(
            """INSERT INTO generated_contract_versions
               (contract_id, version_number, content, change_type, change_description)
               VALUES (%(id)s, %(version)s, %(content)s, %(type)s, %(description)s)""",
            {"id": contract_id, "version": next_ver, "content": content, "type": change_type, "description": description},
        )
        cursor.execute(
            f"""UPDATE generated_contracts SET current_content = %(content)s, updated_at = CURRENT_TIMESTAMP
                 WHERE id = %(id)s RETURNING {CONTRACT_COLUMNS}""",
            {"id": contract_id, "content": content},
        )
        result = dict(cursor.fetchone())
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def complete_generation(contract_id: str, content: str, prompt_version: str, model_name: str) -> tuple[dict[str, Any], bool]:
    conn = get_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT status, user_id FROM generated_contracts WHERE id = %(id)s FOR UPDATE", {"id": contract_id})
        row = cursor.fetchone()
        if not row:
            raise LookupError("Contract not found")
        if row["status"] == "completed":
            conn.rollback()
            return {}, False
        cursor.execute(
            """INSERT INTO generated_contract_versions
               (contract_id, version_number, content, change_type, change_description)
               VALUES (%(id)s, 1, %(content)s, 'IA', 'Generación inicial por IA')
               ON CONFLICT (contract_id, version_number) DO UPDATE SET content = EXCLUDED.content""",
            {"id": contract_id, "content": content},
        )
        period = date.today().replace(day=1)
        cursor.execute(
            """INSERT INTO user_monthly_usage (user_id, period_start, contracts_generated)
               VALUES (%(uid)s, %(period)s, 1)
               ON CONFLICT (user_id, period_start) DO UPDATE
               SET contracts_generated = user_monthly_usage.contracts_generated + 1""",
            {"uid": row["user_id"], "period": period},
        )
        cursor.execute(
            f"""UPDATE generated_contracts SET current_content=%(content)s, status='completed', error_message=NULL,
                 generation_prompt_version=%(prompt)s, model_name=%(model)s,
                 generation_finished_at=CURRENT_TIMESTAMP, usage_counted_at=CURRENT_TIMESTAMP,
                 updated_at=CURRENT_TIMESTAMP
                 WHERE id=%(id)s RETURNING {CONTRACT_COLUMNS}""",
            {"id": contract_id, "content": content, "prompt": prompt_version, "model": model_name},
        )
        result = dict(cursor.fetchone())
        conn.commit()
        return result, True
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
