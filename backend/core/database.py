
import sys
import os
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'
    
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from core.config import settings
from typing import Optional, Dict, Any, List
import re
import logging

logger = logging.getLogger(__name__)

def parse_db_url(url: str) -> dict:
    pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
    match = re.match(pattern, url)
    if not match:
        raise ValueError(f"Invalid database URL format: {url}")
    
    user, password, host, port, database = match.groups()
    return {
        'user': user,
        'password': password,
        'host': host,
        'port': int(port),
        'database': database
    }

try:
    db_params = parse_db_url(settings.database_url)
    logger.info("Database parameters parsed successfully")
except Exception as error:
    logger.warning(f"Could not parse database URL: {error}")
    db_params = None

_pool = None


def _init_pool():
    global _pool
    if _pool is None and db_params:
        logger.info("Inicializando pool de conexiones DB (min=2, max=10)")
        _pool = ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            user=db_params['user'],
            password=db_params['password'],
            host=db_params['host'],
            port=db_params['port'],
            database=db_params['database'],
            client_encoding='UTF8'
        )
        logger.info("Pool de conexiones DB inicializado")
    return _pool


def get_connection():
    pool = _init_pool()
    if pool is None:
        raise Exception("Database parameters not available")
    return pool.getconn()


def release_connection(conn):
    pool = _init_pool()
    if pool and conn:
        try:
            pool.putconn(conn)
        except Exception:
            pass


def execute_query(query: str, params: dict = None) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        result = [dict(row) for row in rows]
        logger.debug("execute_query: %d filas | %s", len(result), query.strip()[:80])
        return result
    except Exception as e:
        logger.error("execute_query ERROR: %s | query=%s", e, query.strip()[:120])
        raise
    finally:
        if conn:
            release_connection(conn)


def execute_insert(query: str, params: dict = None) -> Dict[str, Any]:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        logger.debug("execute_insert OK | %s", query.strip()[:80])
        return dict(row) if row else None
    except Exception as e:
        logger.error("execute_insert ERROR: %s | query=%s", e, query.strip()[:120])
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            release_connection(conn)


def execute_insert_returning(query: str, params: dict = None) -> Dict[str, Any]:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        logger.debug("execute_insert_returning OK | %s", query.strip()[:80])
        return dict(row) if row else None
    except Exception as e:
        logger.error("execute_insert_returning ERROR: %s | query=%s", e, query.strip()[:120])
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            release_connection(conn)


def execute_update(query: str, params: dict = None) -> int:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        rowcount = cursor.rowcount
        cursor.close()
        logger.debug("execute_update: %d filas afectadas | %s", rowcount, query.strip()[:80])
        return rowcount
    except Exception as e:
        logger.error("execute_update ERROR: %s | query=%s", e, query.strip()[:120])
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            release_connection(conn)


def execute_delete(query: str, params: dict = None) -> int:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        rowcount = cursor.rowcount
        cursor.close()
        logger.debug("execute_delete: %d filas eliminadas | %s", rowcount, query.strip()[:80])
        return rowcount
    except Exception as e:
        logger.error("execute_delete ERROR: %s | query=%s", e, query.strip()[:120])
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            release_connection(conn)


def execute_transaction(operations: List[tuple]) -> List[Any]:
    conn = None
    logger.debug("execute_transaction: %d operaciones", len(operations))
    try:
        results = []
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        for query, params in operations:
            cursor.execute(query, params)
            
            try:
                row = cursor.fetchone()
                if row:
                    results.append(dict(row))
                else:
                    results.append(None)
            except:
                results.append(cursor.rowcount)
        
        conn.commit()
        cursor.close()
        logger.debug("execute_transaction OK: %d resultados", len(results))
        return results
    except Exception as e:
        logger.error("execute_transaction ERROR: %s", e)
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            release_connection(conn)


def close_all_connections():
    global _pool
    if _pool:
        logger.info("Cerrando todas las conexiones del pool de BD")
        _pool.closeall()
        _pool = None
