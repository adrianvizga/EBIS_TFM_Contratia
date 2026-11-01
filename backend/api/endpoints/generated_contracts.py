from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
import uuid
import logging
import json
import os

from core.security import get_current_user
from core.database import execute_query, execute_insert_returning, execute_update
from services.contracts.contracts_service import enqueue_contract_analysis
from services.notifications import create_notification
from services.guardrails import check_input
from services.contract_coverage import public_contract_catalog, require_supported_contract_type
from services.usage_service import (
    can_generate_contract, can_modify_with_ai, can_analyze_contract,
    increment_ai_modifications, increment_contracts_analyzed,
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/contract-types")
async def get_contract_types():
    return public_contract_catalog()


class ContractCreate(BaseModel):

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=255)
    contract_type: str
    country: Literal["España"] = "España"
    language: Literal["Español"] = "Español"
    tone: Literal["Legal Formal", "Lenguaje claro"] = "Legal Formal"
    contract_details: Optional["ContractDetails"] = None


class ContractParties(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    partyA: str = Field(default="[PARTE A]", min_length=1, max_length=300)
    partyB: str = Field(default="[PARTE B]", min_length=1, max_length=300)


class ContractDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    parties: ContractParties = Field(default_factory=ContractParties)
    description: str = Field(default="", max_length=8_000)

class ContractUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    content: str = Field(min_length=400, max_length=200_000)
    change_type: str = "Manual"
    change_description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("change_type")
    @classmethod
    def manual_changes_only(cls, value: str) -> str:
        if value != "Manual":
            raise ValueError("Solo se permiten cambios manuales desde este endpoint")
        return value

class ContractResponse(BaseModel):

    id: str
    title: str
    contract_type: str
    country: str
    language: str
    tone: str
    status: str
    current_content: str
    contract_details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    generation_prompt_version: Optional[str] = None
    model_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class VersionResponse(BaseModel):

    id: str
    version_number: Optional[int]
    content: str
    change_type: str
    change_description: Optional[str]
    created_at: datetime


@router.get("/api/generated-contracts", response_model=List[ContractResponse])
async def get_generated_contracts(current_user: dict = Depends(get_current_user)):
    try:
        logger.debug("get_generated_contracts: user_id=%s", current_user.get('id'))
        query = """
            SELECT id::text, title, contract_type, country, language, tone, status, current_content, contract_details,
                   error_message, generation_prompt_version, model_name, created_at, updated_at
            FROM generated_contracts
            WHERE user_id = %(user_id)s
            ORDER BY updated_at DESC
        """
        rows = execute_query(query, {"user_id": current_user['id']})
        return rows
    except Exception as e:
        logger.error(f"Error listing generated contracts: {e}")
        raise HTTPException(status_code=500, detail="Error listing contracts")

@router.post("/api/generated-contracts", response_model=ContractResponse)
async def create_generated_contract(contract: ContractCreate, current_user: dict = Depends(get_current_user)):
    from workers.tasks import generate_contract_task
    import uuid as uuid_lib
    import psycopg2
    import psycopg2.extras
    from core.database import get_connection, release_connection

    try:
        user_id = current_user['id']
        user_role = str(current_user.get('role', '1'))

        try:
            coverage = require_supported_contract_type(contract.contract_type)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        description = contract.contract_details.description if contract.contract_details else ''
        guardrail_text = f"{contract.title} {contract.contract_type} {description}"
        is_allowed, rejection_msg = check_input(guardrail_text, service="generation")
        if not is_allowed:
            logger.info(f"Guardrail rejected generation input from user {user_id}")
            raise HTTPException(status_code=422, detail=rejection_msg)

        if not can_generate_contract(str(user_id), user_role):
            raise HTTPException(
                status_code=403,
                detail="Has alcanzado el límite mensual de contratos generados en tu plan actual. Mejora tu plan para continuar."
            )

        contract_id = str(uuid_lib.uuid4())
        contract_data = contract.model_dump()
        contract_data['contract_type'] = coverage['id']
        contract_details_json = json.dumps(contract_data.get('contract_details', {}))

        logger.info("Creando contrato: contract_id=%s user_id=%s", contract_id, user_id)
        conn = get_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            logger.debug("Insertando contrato en BD: id=%s", contract_id)
            cursor.execute(
                """
                INSERT INTO generated_contracts (
                    id, user_id, title, contract_type, country, language, tone,
                    status, current_content, contract_details
                ) VALUES (
                    %(id)s, %(user_id)s, %(title)s, %(contract_type)s, %(country)s,
                    %(language)s, %(tone)s, %(status)s, %(current_content)s, %(contract_details)s
                ) RETURNING id::text, title, contract_type, country, language, tone,
                            status, current_content, contract_details, error_message,
                            generation_prompt_version, model_name, created_at, updated_at
                """,
                {
                    'id': contract_id,
                    'user_id': user_id,
                    'title': contract_data.get('title', 'Sin título'),
                    'contract_type': contract_data.get('contract_type', 'General'),
                    'country': 'España',
                    'language': 'Español',
                    'tone': contract_data.get('tone', 'Legal Formal'),
                    'status': 'pending',
                    'current_content': '',
                    'contract_details': contract_details_json,
                }
            )
            new_contract = dict(cursor.fetchone())
            logger.debug("Contrato insertado en BD: id=%s", new_contract.get('id'))

            conn.commit()
            cursor.close()
        except Exception as inner_exc:
            logger.error("Error al insertar contrato en BD: %s", inner_exc, exc_info=True)
            conn.rollback()
            raise
        finally:
            release_connection(conn)

        logger.info("Contrato %s creado exitosamente", contract_id)

        try:
            generate_contract_task.delay(contract_id)
        except Exception as e:
            logger.error("No se pudo lanzar tarea Celery para contrato %s: %s", contract_id, e)
            execute_update(
                "UPDATE generated_contracts SET status='error', error_message=%(msg)s WHERE id=%(id)s",
                {"id": contract_id, "msg": "No se pudo iniciar la generación. Puedes reintentarlo."},
            )
            raise HTTPException(status_code=503, detail="No se pudo iniciar la generación. Inténtalo de nuevo.")

        return new_contract

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating generated contract: {e}", exc_info=True)

        try:
            create_notification(
                user_id=str(current_user['id']),
                title="Error al crear contrato",
                message=f"No se pudo crear el contrato '{contract.title}'. Por favor, inténtalo de nuevo.",
                notification_type="error"
            )
        except Exception:
            pass

        raise HTTPException(status_code=500, detail="Error creating contract")

@router.get("/api/generated-contracts/{contract_id}", response_model=ContractResponse)
async def get_generated_contract(contract_id: str, current_user: dict = Depends(get_current_user)):
    try:
        logger.debug("get_generated_contract: contract_id=%s, user_id=%s", contract_id, current_user.get('id'))
        query = """
            SELECT id::text, title, contract_type, country, language, tone, status, current_content, contract_details,
                   error_message, generation_prompt_version, model_name, created_at, updated_at
            FROM generated_contracts
            WHERE id = %(id)s AND user_id = %(user_id)s
        """
        rows = execute_query(query, {"id": contract_id, "user_id": current_user['id']})
        if not rows:
            raise HTTPException(status_code=404, detail="Contract not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting generated contract: {e}")
        raise HTTPException(status_code=500, detail="Error getting contract")

@router.put("/api/generated-contracts/{contract_id}")
async def update_generated_contract(contract_id: str, update: ContractUpdate, current_user: dict = Depends(get_current_user)):
    try:
        logger.debug(f"update_generated_contract called for {contract_id}")
        
        verify_query = "SELECT id FROM generated_contracts WHERE id = %(id)s AND user_id = %(user_id)s"
        if not execute_query(verify_query, {"id": contract_id, "user_id": current_user['id']}):
             raise HTTPException(status_code=404, detail="Contract not found")

        logger.debug(f"Ownership verified for contract {contract_id}")

        from services.generated_contracts_repository import save_version
        updated_contract = save_version(
            contract_id, update.content, "Manual", update.change_description or "Actualización manual"
        )

        result = dict(updated_contract)
        for key in ['created_at', 'updated_at']:
            if key in result and hasattr(result[key], 'isoformat'):
                result[key] = result[key].isoformat()
        
        logger.debug(f"Returning updated contract {contract_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error updating contract: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error updating contract")

@router.delete("/api/generated-contracts/{contract_id}")
async def delete_generated_contract(contract_id: str, current_user: dict = Depends(get_current_user)):
    try:
        verify_query = "SELECT id FROM generated_contracts WHERE id = %(id)s AND user_id = %(user_id)s"
        if not execute_query(verify_query, {"id": contract_id, "user_id": current_user['id']}):
            raise HTTPException(status_code=404, detail="Contract not found")

        delete_versions_query = "DELETE FROM generated_contract_versions WHERE contract_id = %(contract_id)s"
        execute_update(delete_versions_query, {"contract_id": contract_id})

        delete_query = "DELETE FROM generated_contracts WHERE id = %(id)s AND user_id = %(user_id)s"
        execute_update(delete_query, {"id": contract_id, "user_id": current_user['id']})

        logger.info(f"Contract {contract_id} and all related records deleted by user {current_user['id']}")
        return {"message": "Contract deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting generated contract: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting contract")


class AIModifyRequest(BaseModel):

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    prompt: str = Field(min_length=10, max_length=4_000)


@router.post("/api/generated-contracts/{contract_id}/generate")
async def ai_modify_contract(contract_id: str, request: AIModifyRequest, current_user: dict = Depends(get_current_user)):
    from services.openai_client import modify_contract_content

    try:
        user_role = str(current_user.get('role', '1'))

        is_allowed, rejection_msg = check_input(request.prompt, service="modification")
        if not is_allowed:
            logger.info(f"Guardrail rejected modification input from user {current_user['id']}")
            raise HTTPException(status_code=422, detail=rejection_msg)

        if not can_modify_with_ai(str(current_user['id']), user_role, contract_id):
            raise HTTPException(
                status_code=403,
                detail="Has alcanzado el límite de modificaciones con IA para este contrato en tu plan actual. Mejora tu plan para continuar."
            )

        query = """
            SELECT id::text, title, contract_type, country, language, tone, status,
                   current_content, contract_details, created_at, updated_at
            FROM generated_contracts
            WHERE id = %(id)s AND user_id = %(user_id)s
        """
        rows = execute_query(query, {"id": contract_id, "user_id": current_user['id']})
        if not rows:
            raise HTTPException(status_code=404, detail="Contract not found")

        contract = rows[0]
        try:
            coverage = require_supported_contract_type(contract['contract_type'])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        current_content = contract['current_content']
        if not current_content or not current_content.strip():
            raise HTTPException(status_code=400, detail="El contrato no tiene contenido para modificar")

        logger.info(f"[AI-MODIFY] Calling LLM for contract {contract_id}. Prompt: {request.prompt[:100]}")
        modified_content = modify_contract_content(
            current_content=current_content,
            user_prompt=request.prompt,
            contract_type=coverage['id']
        )

        if not modified_content or not modified_content.strip():
            raise HTTPException(status_code=500, detail="La IA no generó contenido válido")

        from services.contract_generation import validate_modified_draft
        validation = validate_modified_draft(current_content, modified_content, coverage['id'])
        if not validation.valid:
            logger.warning("Invalid AI modification for %s: %s", contract_id, validation.errors)
            raise HTTPException(status_code=502, detail="La IA no devolvió una modificación contractual válida")
        from services.generated_contracts_repository import save_version
        updated_contract = save_version(contract_id, modified_content, "IA", request.prompt[:500])
        next_ver = "nueva"

        logger.info(f"[AI-MODIFY] Contract {contract_id} modified with AI. Version {next_ver} created.")

        increment_ai_modifications(str(current_user['id']), contract_id)

        create_notification(
            user_id=str(current_user['id']),
            title="Contrato modificado con IA",
            message=f"El contrato '{contract['title']}' ha sido modificado correctamente por la IA.",
            notification_type="success",
            related_entity_type="generated_contract",
            related_entity_id=contract_id
        )

        result = dict(updated_contract)
        for key in ['created_at', 'updated_at']:
            if key in result and hasattr(result[key], 'isoformat'):
                result[key] = result[key].isoformat()

        return result

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error modifying contract with AI: {e}", exc_info=True)

        try:
            create_notification(
                user_id=str(current_user['id']),
                title="Error en modificación IA",
                message=f"No se pudo modificar el contrato con IA. Por favor, inténtalo de nuevo.",
                notification_type="error",
                related_entity_type="generated_contract",
                related_entity_id=contract_id
            )
        except Exception:
            pass

        raise HTTPException(status_code=500, detail="Error al modificar con IA")


@router.post("/api/generated-contracts/{contract_id}/retry", response_model=ContractResponse)
async def retry_generated_contract(contract_id: str, current_user: dict = Depends(get_current_user)):
    from workers.tasks import generate_contract_task
    rows = execute_query(
        """SELECT id::text, title, contract_type, country, language, tone, status, current_content,
                  contract_details, error_message, generation_prompt_version, model_name, created_at, updated_at
           FROM generated_contracts WHERE id=%(id)s AND user_id=%(uid)s""",
        {"id": contract_id, "uid": current_user["id"]},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Contract not found")
    contract = rows[0]
    if contract["status"] != "error":
        raise HTTPException(status_code=409, detail="Solo se pueden reintentar generaciones con error")
    if not can_generate_contract(str(current_user["id"]), str(current_user.get("role", "1"))):
        raise HTTPException(status_code=403, detail="Has alcanzado el límite mensual de generación")
    execute_update("UPDATE generated_contracts SET status='pending', error_message=NULL WHERE id=%(id)s", {"id": contract_id})
    try:
        generate_contract_task.delay(contract_id)
    except Exception:
        execute_update(
            "UPDATE generated_contracts SET status='error', error_message=%(msg)s WHERE id=%(id)s",
            {"id": contract_id, "msg": "No se pudo iniciar el reintento."},
        )
        raise HTTPException(status_code=503, detail="No se pudo iniciar el reintento")
    contract["status"] = "pending"
    contract["error_message"] = None
    return contract


@router.post("/api/generated-contracts/{contract_id}/send-to-analysis")
async def send_generated_contract_to_analysis(contract_id: str, current_user: dict = Depends(get_current_user)):
    try:
        user_role = str(current_user.get('role', '1'))

        if not can_analyze_contract(str(current_user['id']), user_role):
            raise HTTPException(
                status_code=403,
                detail="Has alcanzado el límite mensual de contratos analizados en tu plan actual. Mejora tu plan para continuar."
            )

        query = """
            SELECT id::text, title, contract_type, current_content
            FROM generated_contracts
            WHERE id = %(id)s AND user_id = %(user_id)s
        """
        rows = execute_query(query, {"id": contract_id, "user_id": current_user['id']})
        if not rows:
            raise HTTPException(status_code=404, detail="Contract not found")

        generated = rows[0]
        try:
            require_supported_contract_type(generated['contract_type'])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        content = generated['current_content']
        if not content or not content.strip():
            raise HTTPException(status_code=400, detail="El contrato no tiene contenido para analizar")

        uploads_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uploads', 'contratos')
        uploads_dir = os.path.abspath(uploads_dir)
        os.makedirs(uploads_dir, exist_ok=True)

        new_contract_id = str(uuid.uuid4())
        filename = f"{new_contract_id}.txt"
        file_path = os.path.join(uploads_dir, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        file_size = os.path.getsize(file_path)
        display_name = f"{generated['title']}.txt"

        contract_insert = """
            INSERT INTO contracts (
                id, user_id, original_file_name, storage_path,
                mime_type, file_size_bytes, page_count, status, uploaded_at
            )
            VALUES (
                %(id)s, %(user_id)s, %(original_file_name)s, %(storage_path)s,
                %(mime_type)s, %(file_size_bytes)s, %(page_count)s, 'pending', CURRENT_TIMESTAMP
            )
            RETURNING id::text
        """
        execute_insert_returning(contract_insert, {
            "id": new_contract_id,
            "user_id": current_user['id'],
            "original_file_name": display_name,
            "storage_path": file_path,
            "mime_type": "text/plain",
            "file_size_bytes": file_size,
            "page_count": None
        })

        analysis_id = str(uuid.uuid4())
        analysis_insert = """
            INSERT INTO contract_analyses (
                id, contract_id, status, overall_risk, started_at
            )
            VALUES (
                %(analysis_id)s, %(contract_id)s, 'processing', 'none', CURRENT_TIMESTAMP
            )
            RETURNING id::text
        """
        execute_insert_returning(analysis_insert, {
            "analysis_id": analysis_id,
            "contract_id": new_contract_id
        })

        enqueue_contract_analysis(new_contract_id)

        increment_contracts_analyzed(str(current_user['id']), user_role)

        create_notification(
            user_id=str(current_user['id']),
            title="Enviado al análisis",
            message=f"El contrato '{generated['title']}' se ha enviado al análisis. Recibirás una notificación cuando finalice.",
            notification_type="info",
            related_entity_type="contract",
            related_entity_id=new_contract_id
        )

        logger.info(f"Generated contract {contract_id} sent to analysis as {new_contract_id}")
        return {
            "id": new_contract_id,
            "filename": display_name,
            "status": "pending",
            "message": "Contrato enviado al análisis correctamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending generated contract to analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al enviar el contrato al análisis")

@router.get("/api/generated-contracts/{contract_id}/versions", response_model=List[VersionResponse])
async def get_contract_versions(contract_id: str, current_user: dict = Depends(get_current_user)):
    try:
        logger.debug("get_contract_versions: contract_id=%s", contract_id)
        verify_query = "SELECT id FROM generated_contracts WHERE id = %(id)s AND user_id = %(user_id)s"
        if not execute_query(verify_query, {"id": contract_id, "user_id": current_user['id']}):
             raise HTTPException(status_code=404, detail="Contract not found")
        
        query = """
            SELECT id::text, version_number, content, change_type, change_description, created_at
            FROM generated_contract_versions
            WHERE contract_id = %(contract_id)s
            ORDER BY created_at DESC
        """
        return execute_query(query, {"contract_id": contract_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing versions: {e}")
        raise HTTPException(status_code=500, detail="Error listing versions")
