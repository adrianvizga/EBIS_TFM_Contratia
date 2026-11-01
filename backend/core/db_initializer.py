
import logging
import os
import time
from pathlib import Path

import psycopg2

from core.security import hash_password


logger = logging.getLogger(__name__)
SCHEMA_VERSION = 'baseline-1'
LEGAL_CONSENT_MIGRATION = 'legal-consent-1'
CONTRACT_ANALYSIS_MIGRATION = 'contract-analysis-2'
CONTRACT_GENERATION_MIGRATION = 'contract-generation-2'
CHATBOT_MIGRATION = 'chatbot-2'
ASPECTS_MIGRATION = 'aspects-unified-1'
DEMO_USER_EMAIL = 'demo@ebistfm.com'
DEMO_USER_FIRST_NAME = 'Demo'
DEMO_USER_LAST_NAME = 'TFM'
DEMO_USER_COMPANY_NAME = 'EBIS Business Techschool'
EXPECTED_TABLES = {
    'users', 'user_settings', 'sessions', 'notifications', 'contracts',
    'contract_analyses', 'contract_clauses', 'contract_risks',
    'contract_aspects', 'contract_missing_elements',
    'clause_relations', 'agent_conversations', 'agent_messages',
    'generated_contracts', 'generated_contract_versions',
    'user_monthly_usage',
}


def _connect_with_retry(database_url: str, attempts: int = 30, delay: float = 2.0):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return psycopg2.connect(database_url)
        except psycopg2.OperationalError as error:
            last_error = error
            logger.warning(
                'PostgreSQL no disponible (intento %s/%s): %s',
                attempt, attempts, error,
            )
            if attempt < attempts:
                time.sleep(delay)
    raise RuntimeError('No se pudo conectar a PostgreSQL') from last_error


def _existing_application_tables(cursor) -> set[str]:
    cursor.execute(
        '''
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
        ''',
        (list(EXPECTED_TABLES),),
    )
    return {row[0] for row in cursor.fetchall()}


def _schema_version(cursor):
    cursor.execute('SELECT to_regclass(%s)', ('public.schema_migrations',))
    if cursor.fetchone()[0] is None:
        return None
    cursor.execute(
        'SELECT version FROM schema_migrations WHERE version = %s',
        (SCHEMA_VERSION,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _record_baseline(cursor):
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(100) PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    cursor.execute(
        '''
        INSERT INTO schema_migrations (version)
        VALUES (%s)
        ON CONFLICT (version) DO NOTHING
        ''',
        (SCHEMA_VERSION,),
    )


def _ensure_legal_consent_schema(cursor):
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS legal_acceptances (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            terms_version VARCHAR(50) NOT NULL,
            privacy_version VARCHAR(50) NOT NULL,
            accepted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_legal_acceptances_user_id ON legal_acceptances(user_id)')
    cursor.execute(
        '''INSERT INTO schema_migrations (version) VALUES (%s)
           ON CONFLICT (version) DO NOTHING''',
        (LEGAL_CONSENT_MIGRATION,),
    )


def _ensure_contract_analysis_schema(cursor):
    cursor.execute(
        "ALTER TABLE contract_clauses ADD COLUMN IF NOT EXISTS order_index INTEGER NOT NULL DEFAULT 0"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_contract_clauses_analysis_order ON contract_clauses(analysis_id, order_index)"
    )
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS contract_analysis_evidence (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            analysis_id UUID NOT NULL REFERENCES contract_analyses(id) ON DELETE CASCADE,
            chunk_id VARCHAR(255), citation VARCHAR(500) NOT NULL,
            law_name VARCHAR(255), law_key VARCHAR(100), article_number VARCHAR(100),
            text_hash VARCHAR(128), score DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_contract_analysis_evidence_analysis_id ON contract_analysis_evidence(analysis_id)"
    )
    cursor.execute(
        '''INSERT INTO schema_migrations (version) VALUES (%s)
           ON CONFLICT (version) DO NOTHING''',
        (CONTRACT_ANALYSIS_MIGRATION,),
    )


def _ensure_contract_generation_schema(cursor):
    for statement in (
        "ALTER TABLE generated_contracts ADD COLUMN IF NOT EXISTS error_message VARCHAR(1000)",
        "ALTER TABLE generated_contracts ADD COLUMN IF NOT EXISTS generation_prompt_version VARCHAR(100)",
        "ALTER TABLE generated_contracts ADD COLUMN IF NOT EXISTS model_name VARCHAR(100)",
        "ALTER TABLE generated_contracts ADD COLUMN IF NOT EXISTS generation_started_at TIMESTAMP",
        "ALTER TABLE generated_contracts ADD COLUMN IF NOT EXISTS generation_finished_at TIMESTAMP",
        "ALTER TABLE generated_contracts ADD COLUMN IF NOT EXISTS usage_counted_at TIMESTAMP",
        "UPDATE generated_contract_versions SET version_number = 1 WHERE version_number IS NULL",
        "UPDATE generated_contract_versions SET change_type = 'IA' WHERE change_type NOT IN ('Manual', 'IA')",
        "ALTER TABLE generated_contract_versions ALTER COLUMN version_number SET NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_generated_contract_versions_number ON generated_contract_versions(contract_id, version_number)",
    ):
        cursor.execute(statement)
    cursor.execute(
        """DO $$ BEGIN
               IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_generated_contracts_status') THEN
                   ALTER TABLE generated_contracts ADD CONSTRAINT ck_generated_contracts_status
                   CHECK (status IN ('pending','processing','completed','error'));
               END IF;
               IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_generated_contract_version_positive') THEN
                   ALTER TABLE generated_contract_versions ADD CONSTRAINT ck_generated_contract_version_positive
                   CHECK (version_number > 0);
               END IF;
               IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_generated_contract_change_type') THEN
                   ALTER TABLE generated_contract_versions ADD CONSTRAINT ck_generated_contract_change_type
                   CHECK (change_type IN ('Manual','IA'));
               END IF;
           END $$"""
    )
    cursor.execute(
        '''INSERT INTO schema_migrations (version) VALUES (%s)
           ON CONFLICT (version) DO NOTHING''',
        (CONTRACT_GENERATION_MIGRATION,),
    )


def _ensure_chatbot_schema(cursor):
    for statement in (
        "ALTER TABLE agent_conversations ADD COLUMN IF NOT EXISTS contract_id UUID REFERENCES contracts(id) ON DELETE SET NULL",
        "ALTER TABLE agent_conversations ADD COLUMN IF NOT EXISTS generated_contract_id UUID REFERENCES generated_contracts(id) ON DELETE SET NULL",
        "ALTER TABLE agent_messages ADD COLUMN IF NOT EXISTS request_id UUID",
        "ALTER TABLE agent_messages ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'completed'",
        "ALTER TABLE agent_messages ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(100)",
        "ALTER TABLE agent_messages ADD COLUMN IF NOT EXISTS model_name VARCHAR(100)",
        "ALTER TABLE agent_messages ADD COLUMN IF NOT EXISTS input_tokens INTEGER",
        "ALTER TABLE agent_messages ADD COLUMN IF NOT EXISTS output_tokens INTEGER",
        "ALTER TABLE agent_messages ADD COLUMN IF NOT EXISTS evidence JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ALTER TABLE agent_messages ADD COLUMN IF NOT EXISTS limitations JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ALTER TABLE agent_messages ADD COLUMN IF NOT EXISTS abstained BOOLEAN NOT NULL DEFAULT FALSE",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_messages_request_role ON agent_messages(conversation_id, request_id, role) WHERE request_id IS NOT NULL",
    ):
        cursor.execute(statement)
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS agent_chat_requests (
               id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
               conversation_id UUID NOT NULL REFERENCES agent_conversations(id) ON DELETE CASCADE,
               request_id UUID NOT NULL,
               status VARCHAR(20) NOT NULL CHECK (status IN ('processing','completed','error')),
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               UNIQUE (conversation_id, request_id)
           )"""
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_chat_requests_conversation ON agent_chat_requests(conversation_id)")
    cursor.execute(
        """DO $$ BEGIN
               IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='update_agent_chat_requests_updated_at') THEN
                   CREATE TRIGGER update_agent_chat_requests_updated_at
                   BEFORE UPDATE ON agent_chat_requests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
               END IF;
           END $$"""
    )
    cursor.execute(
        """DO $$ BEGIN
               IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_agent_message_status') THEN
                   ALTER TABLE agent_messages ADD CONSTRAINT ck_agent_message_status
                   CHECK (status IN ('completed','error'));
               END IF;
               IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fk_agent_conversation_generated_contract') THEN
                   ALTER TABLE agent_conversations ADD CONSTRAINT fk_agent_conversation_generated_contract
                   FOREIGN KEY (generated_contract_id) REFERENCES generated_contracts(id) ON DELETE SET NULL;
               END IF;
           END $$"""
    )
    cursor.execute(
        '''INSERT INTO schema_migrations (version) VALUES (%s)
           ON CONFLICT (version) DO NOTHING''',
        (CHATBOT_MIGRATION,),
    )


def _ensure_aspects_schema(cursor):
    cursor.execute(
        """DO $$ BEGIN
               IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'aspect_type') THEN
                   CREATE TYPE aspect_type AS ENUM ('positive', 'negative');
               END IF;
           END $$"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS contract_aspects (
               id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
               analysis_id UUID NOT NULL REFERENCES contract_analyses(id) ON DELETE CASCADE,
               clause_id UUID REFERENCES contract_clauses(id) ON DELETE SET NULL,
               title VARCHAR(255) NOT NULL,
               description TEXT,
               type aspect_type NOT NULL,
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aspects_analysis_id ON contract_aspects(analysis_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aspects_type ON contract_aspects(type)")
    cursor.execute(
        """DO $$ BEGIN
               IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='update_aspects_updated_at') THEN
                   CREATE TRIGGER update_aspects_updated_at
                   BEFORE UPDATE ON contract_aspects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
               END IF;
           END $$"""
    )
    cursor.execute(
        """DO $$ BEGIN
               IF EXISTS (
                   SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = 'contract_positive_aspects'
               ) THEN
                   INSERT INTO contract_aspects (id, analysis_id, clause_id, title, description, type, created_at, updated_at)
                   SELECT id, analysis_id, clause_id, title, description, 'positive', created_at, updated_at
                   FROM contract_positive_aspects
                   ON CONFLICT (id) DO NOTHING;
                   DROP TABLE contract_positive_aspects;
               END IF;
           END $$"""
    )
    cursor.execute(
        '''INSERT INTO schema_migrations (version) VALUES (%s)
           ON CONFLICT (version) DO NOTHING''',
        (ASPECTS_MIGRATION,),
    )


def _ensure_demo_user(cursor, password: str) -> str | None:
    cursor.execute(
        "SELECT id FROM users WHERE email = %s",
        (DEMO_USER_EMAIL,),
    )
    existing_user = cursor.fetchone()

    if existing_user:
        user_id = existing_user[0]
        cursor.execute(
            """
            UPDATE users
            SET role = %s,
                is_active = TRUE
            WHERE email = %s
            """,
            ('0', DEMO_USER_EMAIL),
        )
    else:
        hashed_password = hash_password(password)
        cursor.execute(
            """
            INSERT INTO users (
                email,
                password_hash,
                first_name,
                last_name,
                company_name,
                role,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING id
            """,
            (
                DEMO_USER_EMAIL,
                hashed_password,
                DEMO_USER_FIRST_NAME,
                DEMO_USER_LAST_NAME,
                DEMO_USER_COMPANY_NAME,
                '0',
            ),
        )
        row = cursor.fetchone()
        user_id = row[0] if row else None

    if user_id is None:
        return None

    cursor.execute(
        "SELECT id FROM user_settings WHERE user_id = %s",
        (user_id,),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO user_settings (user_id) VALUES (%s)",
            (user_id,),
        )

    return str(user_id)


def _prepare_demo_user(cursor) -> None:
    enabled = os.getenv('DEMO_USER_ENABLED', 'false').strip().lower()
    if enabled not in {'1', 'true', 'yes', 'on'}:
        logger.info('Creación del usuario demo deshabilitada')
        return

    password = os.getenv('DEMO_USER_PASSWORD', 'demo')
    if not password:
        raise ValueError('DEMO_USER_PASSWORD no puede estar vacía')

    demo_user_id = _ensure_demo_user(cursor, password)
    if demo_user_id:
        logger.info('Usuario demo preparado correctamente: %s', DEMO_USER_EMAIL)
    else:
        raise RuntimeError(f'No se pudo preparar el usuario demo: {DEMO_USER_EMAIL}')


def initialize_database() -> bool:
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error('DATABASE_URL no está definida')
        return False

    schema_path = Path(__file__).resolve().parent.parent / 'database.sql'
    if not schema_path.exists():
        logger.error('No se encuentra el esquema: %s', schema_path)
        return False

    connection = None
    try:
        connection = _connect_with_retry(database_url)
        connection.autocommit = False
        cursor = connection.cursor()

        existing = _existing_application_tables(cursor)
        missing = EXPECTED_TABLES - existing
        version = _schema_version(cursor)

        if version and not missing:
            logger.info('Esquema PostgreSQL %s ya inicializado', version)
            _ensure_legal_consent_schema(cursor)
            _ensure_contract_analysis_schema(cursor)
            _ensure_contract_generation_schema(cursor)
            _ensure_chatbot_schema(cursor)
            _ensure_aspects_schema(cursor)
            _prepare_demo_user(cursor)
            connection.commit()
            return True

        if existing and missing:
            raise RuntimeError(
                'Esquema PostgreSQL parcial. Tablas presentes: '
                f'{sorted(existing)}. Tablas ausentes: {sorted(missing)}'
            )

        if not existing:
            logger.info('Base de datos vacía; aplicando %s', schema_path)
            cursor.execute(schema_path.read_text(encoding='utf-8'))
        else:
            logger.info('Esquema existente completo; adoptando versión baseline')

        _record_baseline(cursor)
        _ensure_legal_consent_schema(cursor)
        _ensure_contract_analysis_schema(cursor)
        _ensure_contract_generation_schema(cursor)
        _ensure_chatbot_schema(cursor)
        _ensure_aspects_schema(cursor)
        _prepare_demo_user(cursor)

        connection.commit()
        logger.info('Esquema PostgreSQL %s preparado correctamente', SCHEMA_VERSION)
        return True
    except Exception:
        if connection:
            connection.rollback()
        logger.exception('No se pudo inicializar PostgreSQL')
        return False
    finally:
        if connection:
            connection.close()
