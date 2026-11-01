import sys
import os
import re
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'database.sql')


@pytest.fixture(scope="module")
def schema_sql() -> str:
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return f.read()


# Helpers
def _find_fk_cascades(sql: str) -> list[tuple[str, str]]:
    # Regex: REFERENCES table_name(col) ON DELETE ACTION
    pattern = r'REFERENCES\s+(\w+)\s*\([^)]+\)\s+ON\s+DELETE\s+(\w+)'
    return re.findall(pattern, sql, re.IGNORECASE)


def _find_enums(sql: str) -> dict[str, list[str]]:
    pattern = r"CREATE\s+TYPE\s+(\w+)\s+AS\s+ENUM\s*\(([^)]+)\)"
    enums = {}
    for match in re.finditer(pattern, sql, re.IGNORECASE):
        name = match.group(1)
        values_raw = match.group(2)
        values = re.findall(r"'([^']+)'", values_raw)
        enums[name] = values
    return enums


def _find_tables(sql: str) -> list[str]:
    return re.findall(r'CREATE\s+TABLE\s+(\w+)', sql, re.IGNORECASE)


def _find_triggers(sql: str) -> list[str]:
    return re.findall(r'CREATE\s+TRIGGER\s+(\w+)', sql, re.IGNORECASE)


def _find_uuid_defaults(sql: str, table: str) -> bool:
    # Look for CREATE TABLE ... id UUID ... DEFAULT uuid_generate_v4()
    table_block = _extract_table_block(sql, table)
    if not table_block:
        return False
    return 'uuid_generate_v4()' in table_block


def _extract_table_block(sql: str, table: str) -> str | None:
    pattern = rf'CREATE\s+TABLE\s+{table}\s*\((.*?)\);'
    m = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
    return m.group(1) if m else None


# Tests

@pytest.mark.integration
class TestDatabaseSchema:

    EXPECTED_TABLES = [
        "users", "user_settings", "sessions", "notifications",
        "contracts", "contract_analyses", "contract_clauses",
        "contract_risks", "contract_aspects",
        "contract_missing_elements", "clause_relations",
        "agent_conversations", "agent_messages",
        "generated_contracts", "generated_contract_versions",
        "user_monthly_usage",
    ]

    def test_all_expected_tables_exist(self, schema_sql):
        tables = _find_tables(schema_sql)
        for expected in self.EXPECTED_TABLES:
            assert expected in tables, f"Table '{expected}' not found in schema"

    def test_uuid_primary_keys(self, schema_sql):
        for table in self.EXPECTED_TABLES:
            assert _find_uuid_defaults(schema_sql, table), (
                f"Table '{table}' does not have uuid_generate_v4() default for PK"
            )

    def test_cascade_deletes_from_users(self, schema_sql):
        cascades = _find_fk_cascades(schema_sql)
        users_cascades = [(t, action) for t, action in cascades if t == 'users']
        assert len(users_cascades) >= 5, (
            f"Expected at least 5 CASCADE FKs to users, found {len(users_cascades)}"
        )
        for _, action in users_cascades:
            assert action.upper() == 'CASCADE', (
                "All FK to users should use ON DELETE CASCADE"
            )

    def test_cascade_deletes_from_contracts_and_analyses(self, schema_sql):
        cascades = _find_fk_cascades(schema_sql)
        contract_cascades = [(t, a) for t, a in cascades
                             if t in ('contracts', 'contract_analyses')]
        for ref_table, action in contract_cascades:
            assert action.upper() in ('CASCADE', 'SET'), (
                f"FK to {ref_table} should be CASCADE or SET NULL"
            )

    def test_unique_email_constraint(self, schema_sql):
        users_block = _extract_table_block(schema_sql, 'users')
        assert users_block is not None
        assert 'UNIQUE' in users_block.upper()
        assert re.search(r'email\s+VARCHAR.*UNIQUE', users_block, re.IGNORECASE), (
            "email column should have UNIQUE constraint"
        )

    def test_enums_defined(self, schema_sql):
        enums = _find_enums(schema_sql)

        assert 'user_role' in enums
        assert set(enums['user_role']) == {'0', '1', '2', '3'}

        assert 'contract_status' in enums
        assert set(enums['contract_status']) == {
            'pending', 'uploaded', 'processing', 'completed', 'error'
        }

        assert 'risk_level' in enums
        assert set(enums['risk_level']) == {
            'none', 'low', 'medium', 'high', 'critical'
        }

        assert 'severity_level' in enums
        assert set(enums['severity_level']) == {'low', 'medium', 'high'}

        assert 'clause_relation_type' in enums
        assert 'contradiction' in enums['clause_relation_type']

        assert 'aspect_type' in enums
        assert set(enums['aspect_type']) == {'positive', 'negative'}

    def test_updated_at_triggers(self, schema_sql):
        triggers = _find_triggers(schema_sql)
        expected_trigger_tables = [
            'users', 'user_settings', 'contract_clauses', 'contracts',
            'contract_analyses', 'contract_risks', 'aspects',
            'missing_elements', 'clause_relations', 'agent_conversations',
            'generated_contracts', 'user_monthly_usage',
        ]
        for table in expected_trigger_tables:
            matching = [t for t in triggers if table in t]
            assert matching, (
                f"No trigger found for table '{table}' in schema"
            )

    def test_auto_settings_trigger(self, schema_sql):
        assert 'create_user_settings_on_register' in schema_sql

    def test_update_function_exists(self, schema_sql):
        assert 'update_updated_at_column' in schema_sql
        assert 'NEW.updated_at' in schema_sql
