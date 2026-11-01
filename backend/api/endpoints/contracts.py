from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from typing import Optional
from pydantic import BaseModel, Field
import logging
import os
import uuid
import asyncio
import json
from fastapi.responses import StreamingResponse

from core.security import get_current_user
from core.database import (
    execute_query, execute_delete, execute_insert_returning,
    execute_transaction, execute_update,
)
from core.rate_limiter import limiter
from services.contracts.contracts_service import enqueue_contract_analysis
from services.notifications import create_notification
from services.usage_service import (
    can_analyze_contract, reserve_contract_analysis, decrement_contracts_analyzed,
)
from services.contract_coverage import get_contract_coverage

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_PAGES = 200
CONTRACT_ANALYSIS_VERSION = "contract-analysis-v3"


def validate_document_content(content: bytes, extension: str) -> None:
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The file content is not a valid PDF.")
    if extension == ".docx" and not content.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="The file content is not a valid DOCX.")
    if extension == ".txt":
        if b"\x00" in content:
            raise HTTPException(status_code=400, detail="The TXT file contains binary data.")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            content.decode("latin-1")


def count_document_pages(file_path: str, file_extension: str) -> Optional[int]:
    logger.debug(f"Counting pages for {file_path} ({file_extension})")
    try:
        file_extension = file_extension.lower()
        
        if file_extension == '.pdf':
            if PdfReader is None:
                logger.warning("PyPDF2 not available for page counting")
                return None
            try:
                with open(file_path, 'rb') as f:
                    pdf = PdfReader(f)
                    count = len(pdf.pages)
                    logger.debug(f"PDF page count: {count}")
                    return count
            except Exception as e:
                logger.error(f"Error counting PDF pages: {str(e)}")
                return None
        
        elif file_extension == '.docx':
            if Document is None:
                logger.warning("python-docx not available for page counting")
                return None
            try:
                doc = Document(file_path)
                num_paragraphs = len(doc.paragraphs)
                num_tables = len(doc.tables)
                
                estimated_pages = max(1, (num_paragraphs + (num_tables * 3)) // 5)
                logger.debug(f"DOCX estimated page count: {estimated_pages}")
                return estimated_pages
            except Exception as e:
                logger.error(f"Error counting DOCX pages: {str(e)}")
                return None
        
        elif file_extension == '.doc':
            logger.warning(".doc format detected, page count estimation not available")
            return None
        
        else:
            logger.warning(f"Unknown file extension: {file_extension}")
            return None
    
    except Exception as e:
        logger.error(f"Unexpected error counting pages: {str(e)}")
        return None

class ContractListItem(BaseModel):

    id: str
    filename: str
    uploadDate: str
    status: str
    riskLevel: str
    riskCount: int
    positiveCount: int
    errorMessage: Optional[str] = None

class ClauseResponse(BaseModel):

    id: str
    number: Optional[str]
    title: Optional[str]
    technicalText: str
    plainLanguage: Optional[str]
    recommendations: Optional[str]
    category: str
    
class RiskFinding(BaseModel):

    title: str
    severity: str
    
class AspectFinding(BaseModel):

    title: str

class MissingElement(BaseModel):

    title: str
    severity: str


class LegalEvidence(BaseModel):
    citation: str
    lawName: Optional[str] = None
    articleNumber: Optional[str] = None
    score: Optional[float] = None
    
class ClauseRelationResponse(BaseModel):

    id: str
    type: str
    fromClauseId: str
    fromClauseTitle: str
    toClauseId: Optional[str]
    toClauseTitle: Optional[str]
    severity: str
    description: str

class ContractAnalysisResponse(BaseModel):

    filename: str
    uploadDate: str
    status: str
    riskLevel: str
    riskCount: int
    positiveCount: int
    negativeCount: int
    missingCount: int
    contractType: Optional[str] = None
    coverageLevel: Optional[str] = None
    coverageNotice: Optional[str] = None
    legalSources: list[str] = Field(default_factory=list)
    pagesCount: Optional[int] = None
    clauses: list[ClauseResponse]
    riskFindings: list[RiskFinding]
    positiveFindings: list[AspectFinding]
    negativeFindings: list[AspectFinding]
    missingElements: list[MissingElement]
    relations: list[ClauseRelationResponse]
    evidence: list[LegalEvidence] = Field(default_factory=list)


class RetryAnalysisResponse(BaseModel):
    contract_id: str
    status: str
    task_id: str


def map_status_db_to_frontend(db_status: str) -> str:
    status_map = {
        'pending': 'pending',
        'uploaded': 'pending',
        'processing': 'analyzing',
        'completed': 'completed',
        'error': 'error'
    }
    return status_map.get(db_status, 'pending')

def map_risk_level_to_category(risk_level: str) -> str:
    if risk_level in ['high', 'critical']:
        return 'risk'
    elif risk_level in ['none', 'low']:
        return 'neutral'
    return 'neutral'

def map_severity_db_to_frontend(severity: str) -> str:
    if not severity:
        return 'baja'
    mapping = {
        'low': 'baja',
        'medium': 'media',
        'high': 'alta'
    }
    return mapping.get(severity, 'baja')

def map_relation_type_db_to_frontend(relation_type: str) -> str:
    mapping = {
        'contradiction': 'contradiccion',
        'dependency': 'dependencia',
        'duplicity': 'duplicidad',
        'reference_to_absent_clause': 'referencia_a_clausula_ausente'
    }
    return mapping.get(relation_type, relation_type)

def map_risk_level_db_to_frontend(risk_level: str) -> str:
    mapping = {
        'none': 'low',
        'low': 'low',
        'medium': 'medium',
        'high': 'high',
        'critical': 'high'
    }
    return mapping.get(risk_level, 'low')


@router.get("/api/contracts", response_model=list[ContractListItem])
async def get_user_contracts(
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["id"]
        logger.debug("get_user_contracts: user_id=%s", user_id)
        
        query = """
        SELECT
            c.id::text,
            c.original_file_name as file_name,
            c.uploaded_at as created_at,
            c.status,
            c.error_message,
            COUNT(DISTINCT cr.id) as risk_count,
            COUNT(DISTINCT ca_pos.id) as positive_count,
            c.overall_risk as max_risk_level
        FROM contracts c
        LEFT JOIN contract_analyses ca ON ca.contract_id = c.id
        LEFT JOIN contract_risks cr ON cr.analysis_id = ca.id
        LEFT JOIN contract_aspects ca_pos ON ca_pos.analysis_id = ca.id AND ca_pos.type = 'positive'
        WHERE c.user_id = %(user_id)s
        GROUP BY c.id, c.original_file_name, c.uploaded_at, c.status, c.error_message, c.overall_risk
        ORDER BY c.uploaded_at DESC
        """
        
        rows = execute_query(query, {"user_id": user_id})
        
        contracts = []
        for row in rows:
            max_risk = row.get('max_risk_level') or 'none'
            risk_level = map_risk_level_db_to_frontend(max_risk)
            
            upload_date = row['created_at'].isoformat() if row['created_at'] else ""
            
            status = map_status_db_to_frontend(row.get('status') or 'uploaded')
            
            contracts.append(ContractListItem(
                id=row['id'],
                filename=row['file_name'],
                uploadDate=upload_date,
                status=status,
                riskLevel=risk_level,
                riskCount=row.get('risk_count') or 0,
                positiveCount=row.get('positive_count') or 0,
                errorMessage=row.get('error_message')
            ))
        
        return contracts
        
    except Exception as e:
        logger.error(f"Error al obtener contratos del usuario: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al obtener la lista de contratos"
        )

@router.get("/api/contracts/{contract_id}/analysis", response_model=ContractAnalysisResponse)
async def get_contract_analysis(
    contract_id: str,
    current_user: dict = Depends(get_current_user)
):
    logger.info("get_contract_analysis: contract_id=%s, user_id=%s", contract_id, current_user.get('id'))
    try:
        user_id = current_user["id"]
        
        contract_query = """
            SELECT c.id::text, c.original_file_name, c.uploaded_at, c.status, 
                   c.overall_risk, c.contract_type, c.page_count
            FROM contracts c
            WHERE c.id = %(contract_id)s AND c.user_id = %(user_id)s
            LIMIT 1
        """
        contract_rows = execute_query(contract_query, {"contract_id": contract_id, "user_id": user_id})
        logger.debug("Contract rows: %d", len(contract_rows) if contract_rows else 0)
        
        if not contract_rows:
            logger.error(f"Contract not found: {contract_id}")
            raise HTTPException(status_code=404, detail="Contract not found")
        
        contract = contract_rows[0]
        
        analysis_query = """
            SELECT id::text, status, overall_risk
            FROM contract_analyses
            WHERE contract_id = %(contract_id)s
            ORDER BY created_at DESC
            LIMIT 1
        """
        analysis_rows = execute_query(analysis_query, {"contract_id": contract_id})
        logger.debug("Analysis rows: %d", len(analysis_rows) if analysis_rows else 0)
        
        if not analysis_rows:
            logger.error(f"Analysis not found for contract: {contract_id}")
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analysis = analysis_rows[0]
        analysis_id = analysis['id']
        
        clauses_query = """
            SELECT id::text, clause_number, title, original_text, 
                   plain_explanation, legal_advice, risk_level
            FROM contract_clauses
            WHERE analysis_id = %(analysis_id)s
            ORDER BY order_index, created_at
        """
        clauses_raw = execute_query(clauses_query, {"analysis_id": analysis_id})
        logger.debug("Clauses: %d", len(clauses_raw))
        
        clauses = []
        for clause in clauses_raw:
            clauses.append(ClauseResponse(
                id=clause['id'],
                number=clause['clause_number'] or "",
                title=clause['title'] or "",
                technicalText=clause['original_text'] or "",
                plainLanguage=clause['plain_explanation'] or "",
                recommendations=clause['legal_advice'] if clause.get('risk_level') in ['high', 'critical', 'medium'] else None,
                category=map_risk_level_to_category(clause.get('risk_level') or 'none')
            ))
        
        risks_query = """
            SELECT title, severity
            FROM contract_risks
            WHERE analysis_id = %(analysis_id)s
            ORDER BY 
                CASE severity 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                END
        """
        risks_raw = execute_query(risks_query, {"analysis_id": analysis_id})
        logger.debug("Risks: %d", len(risks_raw))
        
        risk_findings = [
            RiskFinding(
                title=risk['title'],
                severity=map_severity_db_to_frontend(risk['severity'])
            )
            for risk in risks_raw
        ]
        
        aspects_query = """
            SELECT title, type
            FROM contract_aspects
            WHERE analysis_id = %(analysis_id)s
            ORDER BY created_at
        """
        aspects_raw = execute_query(aspects_query, {"analysis_id": analysis_id})
        logger.debug("Aspects: %d", len(aspects_raw))

        positive_findings = [
            AspectFinding(title=a['title'])
            for a in aspects_raw if a['type'] == 'positive'
        ]
        negative_findings = [
            AspectFinding(title=a['title'])
            for a in aspects_raw if a['type'] == 'negative'
        ]
        
        missing_query = """
            SELECT title, severity
            FROM contract_missing_elements
            WHERE analysis_id = %(analysis_id)s
            ORDER BY 
                CASE severity 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                END
        """
        missing_raw = execute_query(missing_query, {"analysis_id": analysis_id})
        logger.debug("Missing: %d", len(missing_raw))
        
        missing_elements = [
            MissingElement(
                title=missing['title'],
                severity=map_severity_db_to_frontend(missing['severity'])
            )
            for missing in missing_raw
        ]

        evidence_raw = execute_query(
            """SELECT citation, law_name, article_number, score
               FROM contract_analysis_evidence
               WHERE analysis_id = %(analysis_id)s
               ORDER BY score DESC NULLS LAST""",
            {"analysis_id": analysis_id},
        )
        evidence = [
            LegalEvidence(
                citation=item["citation"], lawName=item.get("law_name"),
                articleNumber=item.get("article_number"), score=item.get("score"),
            ) for item in evidence_raw
        ]
        
        relations_query = """
            SELECT 
                cr.id::text,
                cr.type,
                cr.from_clause_id::text,
                fc.clause_number as from_clause_number,
                fc.title as from_clause_title,
                cr.to_clause_id::text,
                tc.clause_number as to_clause_number,
                tc.title as to_clause_title,
                cr.severity,
                cr.description
            FROM clause_relations cr
            JOIN contract_clauses fc ON cr.from_clause_id = fc.id
            LEFT JOIN contract_clauses tc ON cr.to_clause_id = tc.id
            WHERE cr.analysis_id = %(analysis_id)s
        """
        relations_raw = execute_query(relations_query, {"analysis_id": analysis_id})
        logger.debug("Relations: %d", len(relations_raw))
        
        relations = []
        for rel in relations_raw:
            relations.append(ClauseRelationResponse(
                id=rel['id'],
                type=map_relation_type_db_to_frontend(rel['type']),
                fromClauseId=rel['from_clause_number'] or rel['from_clause_id'],
                fromClauseTitle=rel['from_clause_title'] or "",
                toClauseId=rel['to_clause_number'] if rel.get('to_clause_id') else None,
                toClauseTitle=rel['to_clause_title'] if rel.get('to_clause_id') else None,
                severity=map_severity_db_to_frontend(rel['severity']),
                description=rel['description'] or ""
            ))
        
        try:
            status_str = str(analysis['status']) if analysis.get('status') else "completed"
            risk_level_str = map_risk_level_db_to_frontend(str(analysis.get('overall_risk') or 'none'))
            contract_type_str = str(contract['contract_type']) if contract.get('contract_type') else None
            coverage = get_contract_coverage(contract_type_str)
            
            logger.info("Construyendo respuesta de analisis...")
            response = ContractAnalysisResponse(
                filename=contract['original_file_name'],
                uploadDate=contract['uploaded_at'].isoformat() if contract['uploaded_at'] else "",
                status=status_str,
                riskLevel=risk_level_str,
                riskCount=len(risk_findings),
                positiveCount=len(positive_findings),
                negativeCount=len(negative_findings),
                missingCount=len(missing_elements),
                contractType=contract_type_str,
                coverageLevel=coverage['coverage_level'] if coverage else None,
                coverageNotice=coverage['coverage_notice'] if coverage else None,
                legalSources=coverage['legal_sources'] if coverage else [],
                pagesCount=contract.get('page_count'),
                clauses=clauses,
                riskFindings=risk_findings,
                positiveFindings=positive_findings,
                negativeFindings=negative_findings,
                missingElements=missing_elements,
                relations=relations,
                evidence=evidence,
            )
            logger.info("Respuesta de analisis lista")
            return response
        except Exception as build_err:
            import traceback
            logger.error("Error construyendo respuesta: %s", traceback.format_exc())
            raise HTTPException(status_code=500, detail="Error building response")
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error getting contract analysis: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail="Error retrieving analysis")


@router.delete("/api/contracts/{contract_id}")
async def delete_contract(contract_id: str, current_user: dict = Depends(get_current_user)):
    logger.info("delete_contract: contract_id=%s, user_id=%s", contract_id, current_user.get('id'))
    try:
        verify_query = """
            SELECT id, storage_path FROM contracts
            WHERE id = %(contract_id)s AND user_id = %(user_id)s
        """
        contract = execute_query(
            verify_query, 
            {"contract_id": contract_id, "user_id": current_user['id']}
        )
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        delete_query = """
            DELETE FROM contracts 
            WHERE id = %(contract_id)s AND user_id = %(user_id)s
        """
        rows_deleted = execute_delete(
            delete_query,
            {"contract_id": contract_id, "user_id": current_user['id']}
        )
        
        if rows_deleted == 0:
            raise HTTPException(status_code=404, detail="Contract not found or already deleted")

        storage_path = contract[0].get("storage_path")
        if storage_path:
            uploads_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uploads'))
            resolved_path = os.path.abspath(storage_path)
            try:
                if os.path.commonpath([uploads_root, resolved_path]) == uploads_root and os.path.isfile(resolved_path):
                    os.remove(resolved_path)
            except OSError:
                logger.warning("Contract row deleted but file removal failed: contract_id=%s", contract_id)
        
        return {"message": "Contract deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting contract: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting contract")


@router.post("/api/contracts/{contract_id}/retry", response_model=RetryAnalysisResponse)
@limiter.limit("5/minute")
async def retry_contract_analysis(
    request: Request,
    contract_id: str,
    current_user: dict = Depends(get_current_user),
):
    rows = execute_query(
        "SELECT id::text, status::text FROM contracts WHERE id = %(id)s AND user_id = %(uid)s",
        {"id": contract_id, "uid": current_user["id"]},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Contract not found")
    if rows[0]["status"] != "error":
        raise HTTPException(status_code=409, detail="Only failed analyses can be retried")

    execute_transaction([
        (
            "UPDATE contracts SET status = 'pending', error_message = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %(id)s RETURNING id::text",
            {"id": contract_id},
        ),
        (
            "UPDATE contract_analyses SET status = 'pending', finished_at = NULL, summary = NULL, updated_at = CURRENT_TIMESTAMP WHERE contract_id = %(id)s RETURNING id::text",
            {"id": contract_id},
        ),
    ])
    try:
        task_id = enqueue_contract_analysis(contract_id)
    except Exception:
        logger.exception("Retry enqueue failed: contract_id=%s", contract_id)
        execute_update(
            "UPDATE contracts SET status = 'error', error_message = %(message)s WHERE id = %(id)s",
            {"id": contract_id, "message": "No se pudo reintentar el análisis en este momento."},
        )
        execute_update(
            "UPDATE contract_analyses SET status = 'error' WHERE contract_id = %(id)s",
            {"id": contract_id},
        )
        raise HTTPException(status_code=503, detail="No se pudo reintentar el análisis en este momento.")

    return RetryAnalysisResponse(contract_id=contract_id, status="pending", task_id=task_id)


@router.post("/api/contracts/upload")
@limiter.limit("10/minute")
async def upload_contract(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id_str = str(current_user['id'])
        user_role = str(current_user.get('role', '1'))
        if not can_analyze_contract(user_id_str, user_role):
            raise HTTPException(
                status_code=403,
                detail="Has alcanzado el límite mensual de contratos analizados en tu plan actual. Mejora tu plan para continuar."
            )

        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        allowed_extensions = {'.pdf', '.docx', '.txt'}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"File type {file_ext} not allowed. Only PDF, DOCX, and TXT are supported.")
        
        uploads_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uploads', 'contratos')
        uploads_dir = os.path.abspath(uploads_dir)
        os.makedirs(uploads_dir, exist_ok=True)
        
        contract_id = str(uuid.uuid4())
        filename = f"{contract_id}{file_ext}"
        file_path = os.path.join(uploads_dir, filename)
        
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE // (1024 * 1024)} MB."
            )

        validate_document_content(content, file_ext)
        
        try:
            with open(file_path, 'wb') as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise HTTPException(status_code=500, detail="Error saving file")
        
        logger.debug(f"Counting pages for {filename}")
        page_count = count_document_pages(file_path, file_ext)
        if page_count is not None and page_count > MAX_PAGES:
            try:
                os.remove(file_path)
            except OSError:
                logger.warning("Could not remove oversized document: %s", file_path)
            raise HTTPException(status_code=400, detail=f"Document has too many pages. Maximum allowed is {MAX_PAGES}.")
        logger.info("Documento procesado: %s (%s paginas)", file.filename, page_count)
        
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
        
        params = {
            "id": contract_id,
            "user_id": current_user['id'],
            "original_file_name": file.filename,
            "storage_path": file_path,
            "mime_type": file.content_type,
            "file_size_bytes": file_size,
            "page_count": page_count
        }
        logger.debug("Insertando contrato en BD: contract_id=%s", contract_id)
        
        analysis_id = str(uuid.uuid4())
        analysis_insert = """
            INSERT INTO contract_analyses (
                id, contract_id, analysis_version, status, overall_risk, started_at
            )
            VALUES (
                %(analysis_id)s, %(contract_id)s, %(version)s, 'pending', 'none', CURRENT_TIMESTAMP
            )
            RETURNING id::text
        """

        usage_reserved = reserve_contract_analysis(user_id_str, user_role)
        if not usage_reserved:
            try:
                os.remove(file_path)
            except OSError:
                logger.warning("Could not remove upload after quota race: %s", file_path)
            raise HTTPException(status_code=403, detail="Has alcanzado el límite mensual de contratos analizados.")

        try:
            execute_transaction([
                (contract_insert, params),
                (analysis_insert, {"analysis_id": analysis_id, "contract_id": contract_id, "version": CONTRACT_ANALYSIS_VERSION}),
            ])
            logger.info("Contract and analysis inserted successfully: contract_id=%s analysis_id=%s", contract_id, analysis_id)
        except Exception as e:
            logger.error("Atomic contract creation failed: %s", e)
            try:
                os.remove(file_path)
            except OSError:
                logger.warning("Could not remove upload after DB failure: %s", file_path)
            decrement_contracts_analyzed(user_id_str)
            raise HTTPException(status_code=500, detail="Error creating contract record")

        try:
            task_id = enqueue_contract_analysis(contract_id)
            logger.info("Analysis enqueued: contract_id=%s task_id=%s", contract_id, task_id)
        except Exception:
            logger.exception("Could not enqueue analysis: contract_id=%s", contract_id)
            if usage_reserved:
                try:
                    decrement_contracts_analyzed(user_id_str)
                except Exception:
                    logger.exception("Could not compensate analysis usage: contract_id=%s", contract_id)
            public_message = "No se pudo iniciar el análisis. Puedes reintentarlo más tarde."
            execute_update(
                "UPDATE contracts SET status = 'error', error_message = %(message)s WHERE id = %(id)s",
                {"id": contract_id, "message": public_message},
            )
            execute_update(
                "UPDATE contract_analyses SET status = 'error', summary = %(message)s, finished_at = CURRENT_TIMESTAMP WHERE id = %(id)s",
                {"id": analysis_id, "message": public_message},
            )
            raise HTTPException(status_code=503, detail=public_message)
        
        return {
            "id": contract_id,
            "filename": file.filename,
            "status": "pending",
            "message": "Contract uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading contract: {str(e)}")

        try:
            create_notification(
                user_id=str(current_user['id']),
                title="Error al subir contrato",
                message=f"No se pudo subir el archivo '{file.filename}'. Por favor, inténtalo de nuevo.",
                notification_type="error"
            )
        except Exception:
            pass

        raise HTTPException(status_code=500, detail="Error uploading contract")


@router.get("/api/contracts/stream")
async def stream_contract_updates(current_user: dict = Depends(get_current_user)):
    async def event_generator():
        try:
            user_id = current_user['id']
            last_state = {}
            last_heartbeat = asyncio.get_running_loop().time()
            
            while True:
                try:
                    query = """
                        SELECT 
                            c.id::text,
                            c.status::text,
                            ca.status::text as analysis_status,
                            ca.overall_risk::text
                        FROM contracts c
                        LEFT JOIN contract_analyses ca ON c.id = ca.contract_id
                        WHERE c.user_id = %(user_id)s
                        AND c.status::text IN ('pending', 'processing', 'completed', 'failed', 'error')
                        ORDER BY c.uploaded_at DESC
                    """
                    
                    contracts = execute_query(query, {"user_id": user_id})
                    
                    for contract in contracts:
                        contract_id = contract['id']
                        current_status = {
                            'status': contract['status'],
                            'analysis_status': contract.get('analysis_status'),
                            'overall_risk': contract.get('overall_risk')
                        }
                        
                        if contract_id not in last_state or last_state[contract_id] != current_status:
                            last_state[contract_id] = current_status
                            
                            mapped_status = map_status_db_to_frontend(contract['status'])
                            
                            event_data = {
                                'contract_id': contract_id,
                                'status': mapped_status,
                                'analysis_status': contract.get('analysis_status'),
                                'overall_risk': contract.get('overall_risk')
                            }
                            
                            yield f"data: {json.dumps(event_data)}\n\n"

                    now = asyncio.get_running_loop().time()
                    if now - last_heartbeat >= 15:
                        yield ": keep-alive\n\n"
                        last_heartbeat = now
                    
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}")
                    await asyncio.sleep(5)
                    
        except asyncio.CancelledError:
            logger.info("SSE connection closed by client")
        except Exception as e:
            logger.error(f"Fatal error in SSE: {e}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
