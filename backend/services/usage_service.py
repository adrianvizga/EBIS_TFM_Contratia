
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from typing import Optional, Dict, Any
import json
import logging

from core.database import execute_query, execute_insert_returning, execute_update

logger = logging.getLogger(__name__)


PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    "0": {
        "label": "Administrador",
        "contracts_generated": None,
        "contracts_analyzed": None,
        "ai_modifications_per_contract": None,
        "agent_access": True,
    },
    "1": {
        "label": "Free",
        "contracts_generated": 1,
        "contracts_analyzed": 3,
        "ai_modifications_per_contract": 3,
        "agent_access": False,
    },
    "2": {
        "label": "Plus",
        "contracts_generated": 10,
        "contracts_analyzed": 10,
        "ai_modifications_per_contract": 30,
        "agent_access": True,
    },
    "3": {
        "label": "Pro",
        "contracts_generated": 30,
        "contracts_analyzed": 25,
        "ai_modifications_per_contract": 50,
        "agent_access": True,
    },
}


def _current_period() -> date:
    today = date.today()
    return today.replace(day=1)


def _ensure_usage_row(user_id: str, period: date) -> None:
    rows = execute_query(
        "SELECT id FROM user_monthly_usage WHERE user_id = %(uid)s AND period_start = %(p)s",
        {"uid": user_id, "p": period},
    )
    if not rows:
        logger.debug("Creando fila de uso mensual: user_id=%s, period=%s", user_id, period)
        execute_insert_returning(
            """INSERT INTO user_monthly_usage (user_id, period_start)
               VALUES (%(uid)s, %(p)s)
               RETURNING id::text""",
            {"uid": user_id, "p": period},
        )


def get_usage(user_id: str, role: str) -> Dict[str, Any]:
    logger.debug("get_usage: user_id=%s, role=%s", user_id, role)
    period = _current_period()
    _ensure_usage_row(user_id, period)

    rows = execute_query(
        """SELECT contracts_generated, contracts_analyzed, ai_modifications,
                  generation_limit_reached_at, analysis_limit_reached_at
           FROM user_monthly_usage
           WHERE user_id = %(uid)s AND period_start = %(p)s""",
        {"uid": user_id, "p": period},
    )
    row = rows[0] if rows else {
        "contracts_generated": 0, "contracts_analyzed": 0, "ai_modifications": {},
        "generation_limit_reached_at": None, "analysis_limit_reached_at": None,
    }

    limits = PLAN_LIMITS.get(str(role), PLAN_LIMITS["1"])

    ai_mods_raw = row.get("ai_modifications") or {}
    if isinstance(ai_mods_raw, str):
        ai_mods_raw = json.loads(ai_mods_raw)

    gen_limit_reached = row.get("generation_limit_reached_at")
    if limits["contracts_generated"] is not None and row["contracts_generated"] >= limits["contracts_generated"] and gen_limit_reached is None:
        execute_update(
            """UPDATE user_monthly_usage
               SET generation_limit_reached_at = CURRENT_TIMESTAMP
               WHERE user_id = %(uid)s AND period_start = %(p)s""",
            {"uid": user_id, "p": period},
        )
        gen_limit_reached = datetime.now()

    analysis_limit_reached = row.get("analysis_limit_reached_at")
    if limits["contracts_analyzed"] is not None and row["contracts_analyzed"] >= limits["contracts_analyzed"] and analysis_limit_reached is None:
        execute_update(
            """UPDATE user_monthly_usage
               SET analysis_limit_reached_at = CURRENT_TIMESTAMP
               WHERE user_id = %(uid)s AND period_start = %(p)s""",
            {"uid": user_id, "p": period},
        )
        analysis_limit_reached = datetime.now()

    gen_reset = None
    if gen_limit_reached and limits["contracts_generated"] is not None:
        gen_reset = (gen_limit_reached + relativedelta(months=1)).date().isoformat()

    analysis_reset = None
    if analysis_limit_reached and limits["contracts_analyzed"] is not None:
        analysis_reset = (analysis_limit_reached + relativedelta(months=1)).date().isoformat()

    return {
        "plan": limits["label"],
        "role": str(role),
        "period_start": period.isoformat(),
        "generation_reset_date": gen_reset,
        "analysis_reset_date": analysis_reset,
        "contracts_generated": row["contracts_generated"],
        "contracts_generated_limit": limits["contracts_generated"],
        "contracts_analyzed": row["contracts_analyzed"],
        "contracts_analyzed_limit": limits["contracts_analyzed"],
        "ai_modifications": ai_mods_raw,
        "ai_modifications_per_contract_limit": limits["ai_modifications_per_contract"],
        "agent_access": limits["agent_access"],
    }


def can_generate_contract(user_id: str, role: str) -> bool:
    limits = PLAN_LIMITS.get(str(role), PLAN_LIMITS["1"])
    if limits["contracts_generated"] is None:
        return True
    usage = get_usage(user_id, role)
    allowed = usage["contracts_generated"] < limits["contracts_generated"]
    if not allowed:
        logger.info("Limite de generacion alcanzado: user_id=%s, role=%s", user_id, role)
    return allowed


def can_analyze_contract(user_id: str, role: str) -> bool:
    limits = PLAN_LIMITS.get(str(role), PLAN_LIMITS["1"])
    if limits["contracts_analyzed"] is None:
        return True
    usage = get_usage(user_id, role)
    allowed = usage["contracts_analyzed"] < limits["contracts_analyzed"]
    if not allowed:
        logger.info("Limite de analisis alcanzado: user_id=%s, role=%s", user_id, role)
    return allowed


def can_modify_with_ai(user_id: str, role: str, contract_id: str) -> bool:
    limits = PLAN_LIMITS.get(str(role), PLAN_LIMITS["1"])
    if limits["ai_modifications_per_contract"] is None:
        return True
    usage = get_usage(user_id, role)
    ai_mods = usage["ai_modifications"]
    current = ai_mods.get(contract_id, 0)
    allowed = current < limits["ai_modifications_per_contract"]
    if not allowed:
        logger.info("Limite de modificaciones IA alcanzado: user_id=%s, contract=%s", user_id, contract_id)
    return allowed


def has_agent_access(role: str) -> bool:
    limits = PLAN_LIMITS.get(str(role), PLAN_LIMITS["1"])
    return limits["agent_access"]



def increment_contracts_generated(user_id: str, role: str = "1") -> None:
    period = _current_period()
    _ensure_usage_row(user_id, period)
    execute_insert_returning(
        """UPDATE user_monthly_usage
           SET contracts_generated = contracts_generated + 1
           WHERE user_id = %(uid)s AND period_start = %(p)s
           RETURNING id::text""",
        {"uid": user_id, "p": period},
    )
    limits = PLAN_LIMITS.get(str(role), PLAN_LIMITS["1"])
    if limits["contracts_generated"] is not None:
        rows = execute_query(
            """SELECT contracts_generated, generation_limit_reached_at
               FROM user_monthly_usage
               WHERE user_id = %(uid)s AND period_start = %(p)s""",
            {"uid": user_id, "p": period},
        )
        if rows and rows[0]["contracts_generated"] >= limits["contracts_generated"] and rows[0]["generation_limit_reached_at"] is None:
            execute_update(
                """UPDATE user_monthly_usage
                   SET generation_limit_reached_at = CURRENT_TIMESTAMP
                   WHERE user_id = %(uid)s AND period_start = %(p)s""",
                {"uid": user_id, "p": period},
            )
    logger.info(f"[USAGE] Incremented contracts_generated for user {user_id}")


def increment_contracts_analyzed(user_id: str, role: str = "1") -> None:
    period = _current_period()
    _ensure_usage_row(user_id, period)
    execute_insert_returning(
        """UPDATE user_monthly_usage
           SET contracts_analyzed = contracts_analyzed + 1
           WHERE user_id = %(uid)s AND period_start = %(p)s
           RETURNING id::text""",
        {"uid": user_id, "p": period},
    )
    limits = PLAN_LIMITS.get(str(role), PLAN_LIMITS["1"])
    if limits["contracts_analyzed"] is not None:
        rows = execute_query(
            """SELECT contracts_analyzed, analysis_limit_reached_at
               FROM user_monthly_usage
               WHERE user_id = %(uid)s AND period_start = %(p)s""",
            {"uid": user_id, "p": period},
        )
        if rows and rows[0]["contracts_analyzed"] >= limits["contracts_analyzed"] and rows[0]["analysis_limit_reached_at"] is None:
            execute_update(
                """UPDATE user_monthly_usage
                   SET analysis_limit_reached_at = CURRENT_TIMESTAMP
                   WHERE user_id = %(uid)s AND period_start = %(p)s""",
                {"uid": user_id, "p": period},
            )
    logger.info(f"[USAGE] Incremented contracts_analyzed for user {user_id}")


def reserve_contract_analysis(user_id: str, role: str = "1") -> bool:
    period = _current_period()
    limit = PLAN_LIMITS.get(str(role), PLAN_LIMITS["1"])["contracts_analyzed"]
    execute_insert_returning(
        """INSERT INTO user_monthly_usage (user_id, period_start)
           VALUES (%(uid)s, %(p)s)
           ON CONFLICT (user_id, period_start) DO UPDATE
           SET updated_at = user_monthly_usage.updated_at
           RETURNING id::text""",
        {"uid": user_id, "p": period},
    )
    result = execute_insert_returning(
        """UPDATE user_monthly_usage
           SET contracts_analyzed = contracts_analyzed + 1,
               analysis_limit_reached_at = CASE
                   WHEN %(limit)s IS NOT NULL AND contracts_analyzed + 1 >= %(limit)s
                   THEN COALESCE(analysis_limit_reached_at, CURRENT_TIMESTAMP)
                   ELSE analysis_limit_reached_at
               END
           WHERE user_id = %(uid)s AND period_start = %(p)s
             AND (%(limit)s IS NULL OR contracts_analyzed < %(limit)s)
           RETURNING id::text""",
        {"uid": user_id, "p": period, "limit": limit},
    )
    reserved = result is not None
    logger.info("[USAGE] Analysis reservation for user %s: %s", user_id, reserved)
    return reserved


def decrement_contracts_analyzed(user_id: str) -> None:
    period = _current_period()
    execute_update(
        """UPDATE user_monthly_usage
           SET contracts_analyzed = GREATEST(contracts_analyzed - 1, 0),
               analysis_limit_reached_at = NULL
           WHERE user_id = %(uid)s AND period_start = %(p)s""",
        {"uid": user_id, "p": period},
    )
    logger.info("[USAGE] Compensated contracts_analyzed for user %s", user_id)


def increment_ai_modifications(user_id: str, contract_id: str) -> None:
    period = _current_period()
    _ensure_usage_row(user_id, period)

    execute_insert_returning(
        """UPDATE user_monthly_usage
           SET ai_modifications = ai_modifications || jsonb_build_object(
               %(cid)s,
               COALESCE((ai_modifications->>%(cid)s)::int, 0) + 1
           )
           WHERE user_id = %(uid)s AND period_start = %(p)s
           RETURNING id::text""",
        {"uid": user_id, "p": period, "cid": contract_id},
    )
    logger.info(f"[USAGE] Incremented ai_modifications for user {user_id}, contract {contract_id}")
