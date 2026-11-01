
from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from core.config import settings
from core.database import execute_delete, execute_insert_returning, execute_query, execute_transaction, execute_update
from core.rate_limiter import limiter
from core.security import get_current_user
from services.chat_service import (
    CHAT_PROMPT_VERSION,
    ChatResourceNotFound,
    ChatServiceError,
    UnsupportedContract,
    generate_chat_response,
)
from services.guardrails import check_input
from services.usage_service import has_agent_access

router = APIRouter()
logger = logging.getLogger(__name__)


def _ts(dt) -> str:
    """Serialize a timezone-naive UTC datetime to ISO 8601 with explicit Z suffix."""
    return dt.isoformat() + "Z" if dt else ""


class UpdateTitle(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatRequest(BaseModel):
    message: str = Field(min_length=3, max_length=settings.chat_max_input_chars)
    contract_id: UUID | None = None
    generated_contract_id: UUID | None = None
    request_id: UUID = Field(default_factory=uuid4)

    @model_validator(mode="after")
    def one_contract_only(self):
        if self.contract_id and self.generated_contract_id:
            raise ValueError("Solo se puede vincular un contrato por conversación")
        return self


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _require_agent_access(current_user: dict) -> None:
    if not has_agent_access(str(current_user.get("role", "1"))):
        raise _error(403, "agent_access_denied", "Tu plan no incluye acceso al asistente jurídico.")


def _conversation(conversation_id: str, user_id: str) -> dict:
    rows = execute_query(
        """SELECT ac.id::text, ac.title, ac.contract_id::text,
                  ac.generated_contract_id::text,
                  (SELECT COUNT(*) FROM agent_messages am WHERE am.conversation_id=ac.id) AS message_count,
                  COALESCE(us.language, 'es') AS language
           FROM agent_conversations ac
           LEFT JOIN user_settings us ON us.user_id=ac.user_id
           WHERE ac.id=%(cid)s AND ac.user_id=%(uid)s""",
        {"cid": conversation_id, "uid": user_id},
    )
    if not rows:
        raise _error(404, "conversation_not_found", "Conversación no encontrada.")
    return rows[0]


@router.get("/api/agent/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    _require_agent_access(current_user)
    rows = execute_query(
        """SELECT ac.id::text, ac.title, ac.contract_id::text,
                  ac.generated_contract_id::text,
                  COALESCE(c.original_file_name, gc.title) AS contract_name,
                  ac.created_at, ac.updated_at, COUNT(am.id) AS message_count
           FROM agent_conversations ac
           LEFT JOIN agent_messages am ON am.conversation_id=ac.id
           LEFT JOIN contracts c ON c.id=ac.contract_id AND c.user_id=ac.user_id
           LEFT JOIN generated_contracts gc ON gc.id=ac.generated_contract_id AND gc.user_id=ac.user_id
           WHERE ac.user_id=%(uid)s
           GROUP BY ac.id, c.original_file_name, gc.title
           ORDER BY ac.updated_at DESC""",
        {"uid": str(current_user["id"])},
    )
    return [{
        **row,
        "created_at": _ts(row.get("created_at")),
        "updated_at": _ts(row.get("updated_at")),
    } for row in rows]


@router.post("/api/agent/conversations")
async def create_conversation(current_user: dict = Depends(get_current_user)):
    _require_agent_access(current_user)
    row = execute_insert_returning(
        """INSERT INTO agent_conversations (user_id, title)
           VALUES (%(uid)s, 'Nueva conversación')
           RETURNING id::text, title, contract_id::text, generated_contract_id::text, created_at, updated_at""",
        {"uid": str(current_user["id"])},
    )
    return {**row, "message_count": 0, "contract_name": None,
            "created_at": _ts(row.get("created_at")), "updated_at": _ts(row.get("updated_at"))}


@router.get("/api/agent/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, current_user: dict = Depends(get_current_user)):
    _require_agent_access(current_user)
    _conversation(conversation_id, str(current_user["id"]))
    rows = execute_query(
        """SELECT id::text, role, content, contract_name, status, evidence, limitations, abstained, created_at
           FROM agent_messages WHERE conversation_id=%(cid)s ORDER BY created_at, CASE role WHEN 'user' THEN 0 ELSE 1 END, id""",
        {"cid": conversation_id},
    )
    return [{**row, "created_at": _ts(row.get("created_at"))} for row in rows]


@router.put("/api/agent/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, data: UpdateTitle, current_user: dict = Depends(get_current_user)):
    _require_agent_access(current_user)
    updated = execute_update(
        """UPDATE agent_conversations SET title=%(title)s
           WHERE id=%(cid)s AND user_id=%(uid)s""",
        {"title": data.title.strip(), "cid": conversation_id, "uid": str(current_user["id"])},
    )
    if not updated:
        raise _error(404, "conversation_not_found", "Conversación no encontrada.")
    return {"message": "Updated"}


@router.delete("/api/agent/conversations/{conversation_id}/context")
async def clear_conversation_context(conversation_id: str, current_user: dict = Depends(get_current_user)):
    _require_agent_access(current_user)
    updated = execute_update(
        """UPDATE agent_conversations SET contract_id=NULL, generated_contract_id=NULL
           WHERE id=%(cid)s AND user_id=%(uid)s""",
        {"cid": conversation_id, "uid": str(current_user["id"])},
    )
    if not updated:
        raise _error(404, "conversation_not_found", "Conversación no encontrada.")
    return {"message": "Context cleared"}


@router.delete("/api/agent/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    _require_agent_access(current_user)
    deleted = execute_delete(
        "DELETE FROM agent_conversations WHERE id=%(cid)s AND user_id=%(uid)s",
        {"cid": conversation_id, "uid": str(current_user["id"])},
    )
    if not deleted:
        raise _error(404, "conversation_not_found", "Conversación no encontrada.")
    return {"message": "Deleted"}


def _serialize_message(row: dict) -> dict:
    return {
        "id": row["id"], "role": row["role"], "content": row["content"],
        "contract_name": row.get("contract_name"), "status": row.get("status", "completed"),
        "citations": row.get("evidence") or [], "limitations": row.get("limitations") or [],
        "abstained": bool(row.get("abstained", False)),
        "created_at": _ts(row.get("created_at")),
    }


@router.post("/api/agent/conversations/{conversation_id}/chat")
@limiter.limit("20/minute")
async def chat(conversation_id: str, body: ChatRequest, request: Request,
               current_user: dict = Depends(get_current_user)):
    _require_agent_access(current_user)
    user_id = str(current_user["id"])
    conversation = _conversation(conversation_id, user_id)

    duplicate = execute_query(
        """SELECT id::text, role, content, contract_name, status, created_at
           FROM agent_messages WHERE conversation_id=%(cid)s AND request_id=%(rid)s
           ORDER BY CASE role WHEN 'user' THEN 0 ELSE 1 END""",
        {"cid": conversation_id, "rid": str(body.request_id)},
    )
    if len(duplicate) == 2:
        return {"user_message": _serialize_message(duplicate[0]), "assistant_message": _serialize_message(duplicate[1])}

    allowed, rejection = check_input(body.message, service="agent")
    if not allowed:
        raise _error(422, "guardrail_rejected", rejection)

    reservation = execute_insert_returning(
        """INSERT INTO agent_chat_requests (conversation_id, request_id, status)
           VALUES (%(cid)s, %(rid)s, 'processing')
           ON CONFLICT (conversation_id, request_id) DO NOTHING
           RETURNING id::text""",
        {"cid": conversation_id, "rid": str(body.request_id)},
    )
    if not reservation:
        raise _error(409, "chat_request_in_progress", "Esta solicitud ya se está procesando.")

    contract_id = str(body.contract_id) if body.contract_id else conversation.get("contract_id")
    generated_id = str(body.generated_contract_id) if body.generated_contract_id else conversation.get("generated_contract_id")
    if body.contract_id:
        generated_id = None
    elif body.generated_contract_id:
        contract_id = None

    try:
        generation = generate_chat_response(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=body.message.strip(),
            language=conversation.get("language") or "es",
            contract_id=contract_id,
            generated_contract_id=generated_id,
        )
    except ChatResourceNotFound:
        execute_update("UPDATE agent_chat_requests SET status='error' WHERE conversation_id=%(cid)s AND request_id=%(rid)s",
                       {"cid": conversation_id, "rid": str(body.request_id)})
        raise _error(404, "contract_not_found", "El contrato no existe, no te pertenece o aún no está disponible.")
    except UnsupportedContract:
        execute_update("UPDATE agent_chat_requests SET status='error' WHERE conversation_id=%(cid)s AND request_id=%(rid)s",
                       {"cid": conversation_id, "rid": str(body.request_id)})
        raise _error(422, "unsupported_contract", "El corpus jurídico actual no cubre este tipo de contrato.")
    except (ChatServiceError, Exception) as exc:
        logger.exception("Fallo al generar respuesta del chatbot: %s", exc)
        execute_update("UPDATE agent_chat_requests SET status='error' WHERE conversation_id=%(cid)s AND request_id=%(rid)s",
                       {"cid": conversation_id, "rid": str(body.request_id)})
        raise _error(503, "chat_temporarily_unavailable", "No se pudo generar la respuesta. Puedes reintentarlo.")

    title = body.message.strip()[:252] + "..." if len(body.message.strip()) > 255 else body.message.strip()
    operations = [
        ("""INSERT INTO agent_messages
              (conversation_id, role, content, contract_name, request_id, status)
             VALUES (%(cid)s, 'user', %(content)s, %(contract_name)s, %(rid)s, 'completed')
             RETURNING id::text, role, content, contract_name, status, created_at""",
         {"cid": conversation_id, "content": body.message.strip(), "contract_name": generation.contract_name,
          "rid": str(body.request_id)}),
        ("""INSERT INTO agent_messages
              (conversation_id, role, content, request_id, status, prompt_version, model_name,
               input_tokens, output_tokens, evidence, limitations, abstained)
             VALUES (%(cid)s, 'assistant', %(content)s, %(rid)s, 'completed', %(prompt)s, %(model)s,
                     %(input_tokens)s, %(output_tokens)s, %(evidence)s::jsonb, %(limitations)s::jsonb, %(abstained)s)
             RETURNING id::text, role, content, contract_name, status, evidence, limitations, abstained, created_at""",
         {"cid": conversation_id, "content": generation.content, "rid": str(body.request_id),
          "prompt": CHAT_PROMPT_VERSION, "model": generation.model_name,
          "input_tokens": generation.input_tokens, "output_tokens": generation.output_tokens,
          "evidence": json.dumps(generation.evidence, ensure_ascii=False),
          "limitations": json.dumps(generation.limitations, ensure_ascii=False), "abstained": generation.abstained}),
        ("""UPDATE agent_conversations
             SET title=CASE WHEN %(first)s THEN %(title)s ELSE title END,
                 contract_id=%(contract_id)s, generated_contract_id=%(generated_id)s,
                 updated_at=CURRENT_TIMESTAMP
             WHERE id=%(cid)s RETURNING id::text""",
         {"first": int(conversation.get("message_count") or 0) == 0, "title": title,
          "contract_id": contract_id, "generated_id": generated_id, "cid": conversation_id}),
        ("""UPDATE agent_chat_requests SET status='completed'
             WHERE conversation_id=%(cid)s AND request_id=%(rid)s RETURNING id::text""",
         {"cid": conversation_id, "rid": str(body.request_id)}),
    ]
    results = execute_transaction(operations)
    return {"user_message": _serialize_message(results[0]), "assistant_message": _serialize_message(results[1])}
