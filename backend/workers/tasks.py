
from workers.celery_app import celery_app
from core.config import settings
from core.database import get_connection, release_connection
import psycopg2.extras
from services.document_text_extractor import extract_text_from_file
from services.openai_client import analyze_contract_with_openai
from services.legal_analysis import analyze_clause_legal, aggregate_analysis
from services.rag_service import retrieve_legal_context
from services.clause_relations_service import detect_absent_clause_references, analyze_clause_relations
from services.notifications import create_notification
from services.contract_coverage import require_supported_contract_type
from services.openai_resilience import RETRYABLE_ERRORS
import logging
import time

logger = logging.getLogger(__name__)
MIN_CONTRACT_CHARS = 1
MAX_CONTRACT_CHARS = 500_000


@celery_app.task(name="analyze_contract", bind=True)
def analyze_contract(self, contract_id: str):
    conn = None
    
    try:
        logger.info("Iniciando tarea de analisis: contract_id=%s", contract_id)
        
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        logger.debug("Conexion DB abierta: contract_id=%s", contract_id)

        cursor.execute("SELECT * FROM contracts WHERE id = %(contract_id)s FOR UPDATE", {"contract_id": contract_id})
        contract = cursor.fetchone()
        
        if not contract:
            logger.warning("Contrato no encontrado: id=%s", contract_id)
            return {"status": "warning", "message": "Contract not found"}

        if str(contract.get('status')) == 'completed':
            logger.info("Tarea duplicada ignorada: contrato ya completado contract_id=%s", contract_id)
            conn.rollback()
            return {"status": "success", "message": "Contract analysis already completed", "contract_id": contract_id}

        cursor.execute("UPDATE contracts SET status = 'processing', error_message = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = %(contract_id)s", {"contract_id": contract_id})
        cursor.execute("UPDATE contract_analyses SET status = 'processing', finished_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE contract_id = %(contract_id)s", {"contract_id": contract_id})
        conn.commit()

        user_id = str(contract['user_id'])
        contract_name = contract['original_file_name'] or "Contrato"
        create_notification(
            user_id=user_id,
            title="Análisis iniciado",
            message=f"Se ha iniciado el análisis del contrato '{contract_name}'.",
            notification_type="info",
            related_entity_type="contract",
            related_entity_id=contract_id
        )

        file_path = contract['storage_path']
        mime_type = contract['mime_type']
        
        logger.info("Extrayendo texto de %s", file_path)
        contract_text = extract_text_from_file(file_path, mime_type)
        
        contract_text = contract_text.strip()
        if len(contract_text) < MIN_CONTRACT_CHARS:
            raise ValueError("No se pudo extraer texto suficiente. Si es un PDF escaneado, necesita OCR.")
        if len(contract_text) > MAX_CONTRACT_CHARS:
            raise ValueError("El texto extraído supera el límite permitido para el análisis.")

        logger.info("Enviando a OpenAI para analisis: contract_id=%s", contract_id)
        analysis_result = analyze_contract_with_openai(contract_text, user_id=user_id)

        clauses_received = analysis_result.get("clauses", [])
        logger.debug("Clausulas recibidas: %d", len(clauses_received))

        metadata = analysis_result.get("contract_metadata", {})
        detected_type = metadata.get("contract_type")
        try:
            coverage = require_supported_contract_type(detected_type)
        except ValueError:
            message = f"Tipo de contrato no soportado por el corpus legal actual: {detected_type or 'desconocido'}"
            cursor.execute("UPDATE contracts SET status = 'error', contract_type = %(type)s, error_message = %(message)s, updated_at = CURRENT_TIMESTAMP WHERE id = %(id)s", {"id": contract_id, "type": detected_type or "otro", "message": message})
            cursor.execute("UPDATE contract_analyses SET status = 'error', summary = %(message)s, finished_at = CURRENT_TIMESTAMP WHERE contract_id = %(id)s", {"id": contract_id, "message": message})
            conn.commit()
            create_notification(user_id=user_id, title="Contrato no soportado", message=message, notification_type="warning", related_entity_type="contract", related_entity_id=contract_id)
            return {"status": "error", "message": message, "unsupported_contract_type": detected_type or "otro"}
        metadata["contract_type"] = coverage["id"]
        
        cursor.execute("""
            UPDATE contracts 
            SET status = 'processing',
                language = %(language)s,
                contract_type = %(contract_type)s,
                page_count = %(page_count)s,
                processed_at = CURRENT_TIMESTAMP,
                overall_risk = 'none',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %(contract_id)s
        """, {
            "contract_id": contract_id,
            "language": metadata.get("detected_language"),
            "contract_type": metadata.get("contract_type"),
            "page_count": contract.get("page_count")
        })
        
        overview = analysis_result.get("analysis_overview", {})
        
        cursor.execute("SELECT id FROM contract_analyses WHERE contract_id = %(contract_id)s ORDER BY created_at DESC LIMIT 1", {"contract_id": contract_id})
        analysis_record = cursor.fetchone()
        
        analysis_id = None
        if analysis_record:
            analysis_id = analysis_record['id']
            cursor.execute("""
                UPDATE contract_analyses
                SET status = 'processing',
                    overall_risk = 'none',
                    summary = %(summary)s,
                    tokens_used = %(tokens_used)s,
                    finished_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %(analysis_id)s
            """, {
                "analysis_id": analysis_id,
                "summary": overview.get("summary"),
                "tokens_used": overview.get("tokens_used_hint")
            })
        else:
             import uuid
             analysis_id = str(uuid.uuid4())
             cursor.execute("""
                INSERT INTO contract_analyses (id, contract_id, status, overall_risk, summary, tokens_used, started_at, finished_at)
                VALUES (%(id)s, %(contract_id)s, 'processing', 'none', %(summary)s, %(tokens_used)s, CURRENT_TIMESTAMP, NULL)
             """, {
                 "id": analysis_id,
                 "contract_id": contract_id,
                 "summary": overview.get("summary"),
                 "tokens_used": overview.get("tokens_used_hint")
             })
        
        clauses = analysis_result.get("clauses", [])
        if clauses and analysis_id:
            cursor.execute("DELETE FROM contract_clauses WHERE analysis_id = %(analysis_id)s", {"analysis_id": analysis_id})
            
            for clause in clauses:
                cursor.execute("""
                    INSERT INTO contract_clauses (
                        id, analysis_id, clause_number, title, original_text, 
                        plain_explanation, legal_advice, risk_level, has_issue, order_index
                    ) VALUES (
                        uuid_generate_v4(), %(analysis_id)s, %(clause_number)s, %(title)s, %(original_text)s,
                        %(plain_explanation)s, %(legal_advice)s, %(risk_level)s, %(has_issue)s, %(order_index)s
                    )
                """, {
                    "analysis_id": analysis_id,
                    "clause_number": clause.get("clause_number"),
                    "title": clause.get("title"),
                    "original_text": clause.get("original_text"),
                    "plain_explanation": clause.get("plain_explanation"),
                    "legal_advice": None,
                    "risk_level": "none",
                    "has_issue": False,
                    "order_index": clause.get("order_index", 0),
                })
        
        
        conn.commit()

        logger.info("Clausulas insertadas: %d | contract_id=%s", len(clauses), contract_id)

        logger.info("Iniciando analisis juridico: contract_id=%s", contract_id)
        
        cursor.execute("DELETE FROM contract_risks WHERE analysis_id = %(aid)s", {"aid": analysis_id})
        cursor.execute("DELETE FROM contract_aspects WHERE analysis_id = %(aid)s", {"aid": analysis_id})
        cursor.execute("DELETE FROM contract_missing_elements WHERE analysis_id = %(aid)s", {"aid": analysis_id})
        conn.commit()
        
        cursor.execute("""
            SELECT id, clause_number, title, original_text, plain_explanation 
            FROM contract_clauses 
            WHERE analysis_id = %(aid)s
            ORDER BY order_index, created_at
        """, {"aid": analysis_id})
        clauses_db = cursor.fetchall()
        
        logger.info("Clausulas a analizar: %d", len(clauses_db))
        
        contract_metadata_context = {
            "contract_type": metadata.get("contract_type", "otro"),
            "language": metadata.get("detected_language", "es"),
            "summary": (overview.get("summary") or "")[:500]
        }
        
        contract_type = metadata.get("contract_type", "otro")
        
        clause_results = []
        total_tokens_phase4 = 0
        all_legal_contexts = []
        
        for idx, clause_row in enumerate(clauses_db, 1):
            logger.info("Analizando clausula %d/%d: %s", idx, len(clauses_db), clause_row['clause_number'] or 'N/A')
            
            clause_dict = {
                "id": str(clause_row['id']),
                "clause_number": clause_row['clause_number'],
                "title": clause_row['title'],
                "original_text": clause_row['original_text'],
                "plain_explanation": clause_row['plain_explanation']
            }
            
            legal_context = retrieve_legal_context(
                clause_text=clause_row['original_text'] or "",
                contract_type=contract_type,
                top_k=5
            )
            if legal_context:
                all_legal_contexts.extend(legal_context)
            
            result = analyze_clause_legal(clause_dict, contract_metadata_context, legal_context=legal_context, user_id=user_id)
            total_tokens_phase4 += result.get("tokens_used", 0)
            
            clause_result = result.get("clause_result", {})
            
            cursor.execute("""
                UPDATE contract_clauses SET
                    risk_level = %(risk_level)s,
                    has_issue = %(has_issue)s,
                    legal_advice = %(legal_advice)s,
                    plain_explanation = %(plain_explanation)s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %(clause_id)s
            """, {
                "clause_id": str(clause_row['id']),
                "risk_level": clause_result.get("risk_level", "none"),
                "has_issue": clause_result.get("has_issue", False),
                "legal_advice": clause_result.get("legal_advice"),
                "plain_explanation": clause_result.get("plain_explanation") or clause_row['plain_explanation']
            })
            
            for risk in result.get("risks_to_create", []):
                raw_severity = risk.get("severity", "low")
                valid_severity = raw_severity if raw_severity in ("low", "medium", "high") else "low"
                
                cursor.execute("""
                    INSERT INTO contract_risks (id, analysis_id, clause_id, title, description, severity, category)
                    VALUES (uuid_generate_v4(), %(analysis_id)s, %(clause_id)s, %(title)s, %(description)s, %(severity)s, %(category)s)
                """, {
                    "analysis_id": analysis_id,
                    "clause_id": str(clause_row['id']),
                    "title": risk.get("title", "Riesgo detectado"),
                    "description": risk.get("description"),
                    "severity": valid_severity,
                    "category": risk.get("category", "general")
                })
            
            for aspect in result.get("aspects_to_create", []):
                aspect_type = aspect.get("type", "positive")
                if aspect_type not in ("positive", "negative"):
                    aspect_type = "positive"
                cursor.execute("""
                    INSERT INTO contract_aspects (id, analysis_id, clause_id, title, description, type)
                    VALUES (uuid_generate_v4(), %(analysis_id)s, %(clause_id)s, %(title)s, %(description)s, %(type)s)
                """, {
                    "analysis_id": analysis_id,
                    "clause_id": str(clause_row['id']),
                    "title": aspect.get("title", "Aspecto detectado"),
                    "description": aspect.get("description"),
                    "type": aspect_type
                })
            
            clause_results.append({
                "clause_number": clause_row['clause_number'],
                "risk_level": clause_result.get("risk_level", "none"),
                "has_issue": clause_result.get("has_issue", False),
                "brief_finding": clause_result.get("legal_advice") or clause_result.get("plain_explanation") or ""
            })
            conn.commit()

        logger.info("Agregando resultados de %d clausulas: contract_id=%s", len(clause_results), contract_id)
        
        seen_citations = set()
        unique_aggregation_context = []
        for ctx in all_legal_contexts:
            cit = ctx.get("citation", "")
            if cit not in seen_citations:
                seen_citations.add(cit)
                unique_aggregation_context.append(ctx)
        unique_aggregation_context = sorted(unique_aggregation_context, key=lambda x: x.get("score", 0), reverse=True)[:10]

        cursor.execute("DELETE FROM contract_analysis_evidence WHERE analysis_id = %(aid)s", {"aid": analysis_id})
        for evidence in unique_aggregation_context:
            if not evidence.get("citation"):
                continue
            cursor.execute("""
                INSERT INTO contract_analysis_evidence (
                    id, analysis_id, chunk_id, citation, law_name, law_key,
                    article_number, text_hash, score
                ) VALUES (
                    uuid_generate_v4(), %(analysis_id)s, %(chunk_id)s, %(citation)s,
                    %(law_name)s, %(law_key)s, %(article_number)s, %(text_hash)s, %(score)s
                )
            """, {
                "analysis_id": analysis_id,
                "chunk_id": evidence.get("chunk_id"),
                "citation": evidence.get("citation"),
                "law_name": evidence.get("law_name"),
                "law_key": evidence.get("law_key"),
                "article_number": evidence.get("article_number"),
                "text_hash": evidence.get("text_hash"),
                "score": evidence.get("score"),
            })
        
        aggregation = aggregate_analysis(clause_results, contract_metadata_context, legal_context=unique_aggregation_context, user_id=user_id)
        total_tokens_phase4 += aggregation.get("tokens_used", 0)
        
        for missing in aggregation.get("missing_elements_to_create", []):
            raw_sev = missing.get("severity", "low")
            valid_sev = raw_sev if raw_sev in ("low", "medium", "high") else "low"
            
            cursor.execute("""
                INSERT INTO contract_missing_elements (id, analysis_id, title, description, suggested_clause, severity, category)
                VALUES (uuid_generate_v4(), %(analysis_id)s, %(title)s, %(description)s, %(suggested_clause)s, %(severity)s, %(category)s)
            """, {
                "analysis_id": analysis_id,
                "title": missing.get("title", "Elemento ausente"),
                "description": missing.get("description"),
                "suggested_clause": missing.get("suggested_clause"),
                "severity": valid_sev,
                "category": missing.get("category", "general")
            })
        
        logger.info("Iniciando analisis de relaciones entre clausulas: contract_id=%s", contract_id)
        
        cursor.execute("DELETE FROM clause_relations WHERE analysis_id = %(aid)s", {"aid": analysis_id})
        conn.commit()
        
        cursor.execute("""
            SELECT id, clause_number, title, original_text, plain_explanation, risk_level
            FROM contract_clauses
            WHERE analysis_id = %(aid)s
            ORDER BY order_index, created_at
        """, {"aid": analysis_id})
        clauses_for_relations = cursor.fetchall()
        
        clauses_dicts = [
            {
                "id": str(row['id']),
                "clause_number": row['clause_number'],
                "title": row['title'],
                "original_text": row['original_text'],
                "plain_explanation": row['plain_explanation'],
                "risk_level": row['risk_level'],
            }
            for row in clauses_for_relations
        ]
        
        total_tokens_phase5 = 0
        
        absent_refs = detect_absent_clause_references(clauses_dicts)
        for ref in absent_refs:
            cursor.execute("""
                INSERT INTO clause_relations (id, analysis_id, type, from_clause_id, to_clause_id, severity, title, description)
                VALUES (uuid_generate_v4(), %(analysis_id)s, 'reference_to_absent_clause', %(from_clause_id)s, NULL, 'medium',
                        %(title)s, %(description)s)
            """, {
                "analysis_id": analysis_id,
                "from_clause_id": ref["from_clause_id"],
                "title": f"Referencia a cláusula ausente ({ref['referenced_number']})",
                "description": f"La cláusula '{ref['clause_title']}' hace referencia a la cláusula {ref['referenced_number']}, que no existe en el contrato."
            })
        
        semantic_relations, tokens_phase5 = analyze_clause_relations(clauses_dicts, user_id=user_id)
        total_tokens_phase5 += tokens_phase5
        
        for rel in semantic_relations:
            rel_type = rel.get("type", "dependency")
            valid_types = ["contradiction", "dependency", "duplicity"]
            if rel_type not in valid_types:
                rel_type = "dependency"
            
            severity = rel.get("severity", "low")
            if severity not in ("low", "medium", "high"):
                severity = "low"
            
            cursor.execute("""
                INSERT INTO clause_relations (id, analysis_id, type, from_clause_id, to_clause_id, severity, title, description)
                VALUES (uuid_generate_v4(), %(analysis_id)s, %(type)s, %(from_clause_id)s, %(to_clause_id)s, %(severity)s, %(title)s, %(description)s)
            """, {
                "analysis_id": analysis_id,
                "type": rel_type,
                "from_clause_id": rel["from_clause_id"],
                "to_clause_id": rel["to_clause_id"],
                "severity": severity,
                "title": rel.get("title", "Relación detectada"),
                "description": rel.get("description", "")
            })
        
        conn.commit()
        logger.info("Relaciones insertadas: absent_refs=%d semanticas=%d | contract_id=%s", len(absent_refs), len(semantic_relations), contract_id)
        
        risk_rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        risk_levels = ["none", "low", "medium", "high", "critical"]

        risk_counts: dict[str, int] = {"none": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
        for item in clause_results:
            lvl = item.get("risk_level", "none")
            risk_counts[lvl] = risk_counts.get(lvl, 0) + 1

        n_critical = risk_counts.get("critical", 0)
        n_high = risk_counts.get("high", 0)
        n_medium = risk_counts.get("medium", 0)

        # Los límites se derivan de la distribución de cláusulas para que un valor
        # atípico no domine la puntuación global y los contratos bien redactados no se penalicen.
        if n_critical >= 1:
            min_risk, max_risk = "high", "critical"
        elif n_high >= 2:
            min_risk, max_risk = "high", "high"
        elif n_high >= 1 or n_medium >= 3:
            min_risk, max_risk = "medium", "high"
        elif n_medium >= 1:
            min_risk, max_risk = "low", "medium"
        else:
            min_risk, max_risk = "none", "low"

        model_overall_risk = aggregation.get("overall_risk", "none")
        model_rank = risk_rank.get(model_overall_risk, 0)
        final_rank = max(risk_rank[min_risk], min(model_rank, risk_rank[max_risk]))
        final_overall_risk = risk_levels[final_rank]
        final_summary = aggregation.get("summary", overview.get("summary", ""))
        total_tokens = (overview.get("tokens_used_hint") or 0) + total_tokens_phase4 + total_tokens_phase5
        
        cursor.execute("""
            UPDATE contract_analyses SET
                status = 'completed',
                overall_risk = %(overall_risk)s,
                summary = %(summary)s,
                tokens_used = %(tokens_used)s,
                finished_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %(analysis_id)s
        """, {
            "analysis_id": analysis_id,
            "overall_risk": final_overall_risk,
            "summary": final_summary,
            "tokens_used": total_tokens
        })
        
        cursor.execute("""
            UPDATE contracts SET
                status = 'completed',
                overall_risk = %(overall_risk)s,
                processed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %(contract_id)s
        """, {
            "contract_id": contract_id,
            "overall_risk": final_overall_risk
        })
        
        conn.commit()
        logger.info("Contrato %s analizado completamente. Riesgo global: %s", contract_id, final_overall_risk)

        risk_label = {"none": "sin riesgo", "low": "bajo", "medium": "medio", "high": "alto"}.get(final_overall_risk, final_overall_risk)
        create_notification(
            user_id=user_id,
            title="Análisis completado",
            message=f"El análisis del contrato '{contract_name}' ha finalizado. Riesgo general: {risk_label}.",
            notification_type="success",
            related_entity_type="contract",
            related_entity_id=contract_id
        )

        return {
            "status": "success",
            "contract_id": contract_id,
            "overall_risk": final_overall_risk,
            "clauses_analyzed": len(clauses_db),
            "relations_found": len(absent_refs) + len(semantic_relations),
            "tokens_used": total_tokens,
            "message": "Contract analysis completed (Phase 3 + Phase 4 + Phase 5)"
        }
        
    except Exception as e:
        logger.error("Error procesando contrato %s: %s", contract_id, str(e), exc_info=True)

        transient_errors = RETRYABLE_ERRORS + (psycopg2.OperationalError,)
        retries = int(getattr(getattr(self, "request", None), "retries", 0) or 0)
        if isinstance(e, transient_errors) and retries < 2:
            if conn:
                conn.rollback()
            countdown = min(2 ** retries, 8)
            logger.warning("Transient analysis failure; retrying contract_id=%s in %ss", contract_id, countdown)
            raise self.retry(exc=e, countdown=countdown, max_retries=2)
        
        if 'user_id' in locals() and user_id:
            error_contract_name = locals().get('contract_name', 'Contrato')
            create_notification(
                user_id=user_id,
                title="Error en el análisis",
                message=f"Ha ocurrido un error al analizar el contrato '{error_contract_name}'. Por favor, inténtalo de nuevo.",
                notification_type="error",
                related_entity_type="contract",
                related_entity_id=contract_id
            )
        
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute("""
                    UPDATE contracts 
                    SET status = 'error',
                        error_message = %(error_message)s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %(contract_id)s
                """, {
                    "contract_id": contract_id,
                    "error_message": "No se pudo completar el análisis. Puedes reintentarlo."
                })
                
                if 'analysis_id' in locals() and analysis_id:
                     cursor.execute("UPDATE contract_analyses SET status = 'error' WHERE id = %(id)s", {"id": analysis_id})
                     
                conn.commit()
            except Exception as commit_error:
                logger.error(f"Failed to update error status: {commit_error}")
                conn.rollback()
        
        raise
        
    finally:
        if conn:
            release_connection(conn)
            logger.info("Conexion DB liberada: contract_id=%s", contract_id)

@celery_app.task(
    name="generate_contract", bind=True, autoretry_for=RETRYABLE_ERRORS,
    retry_backoff=True, retry_kwargs={"max_retries": 2},
)
def generate_contract_task(self, contract_id: str):
    from services.openai_client import generate_contract_content
    from services.contract_generation import GENERATION_PROMPT_VERSION, validate_generated_draft
    from services.generated_contracts_repository import complete_generation
    import uuid as uuid_lib
    
    conn = None
    contract_uuid = contract_id  # Initialize for exception handler
    def safe_notification(**kwargs):
        try:
            create_notification(**kwargs)
        except Exception:
            logger.warning("No se pudo crear la notificación de generación", exc_info=True)
    
    try:
        logger.info("Iniciando tarea de generacion: contract_id=%s", contract_id)
        
        try:
            contract_uuid = str(uuid_lib.UUID(contract_id)) if isinstance(contract_id, str) else contract_id
        except (ValueError, AttributeError) as exc:
            raise ValueError("Identificador de contrato inválido") from exc
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
        logger.info(f"Looking for contract with UUID: {contract_uuid}")
        
        cursor.execute("""SELECT gc.*, u.role::text AS user_role FROM generated_contracts gc
                          JOIN users u ON u.id = gc.user_id
                          WHERE gc.id = %(contract_id)s FOR UPDATE OF gc""", {"contract_id": contract_uuid})
        contract = cursor.fetchone()
        
        if not contract:
            logger.error("Contrato %s no encontrado en base de datos", contract_id)
            cursor.execute("SELECT id, user_id, title FROM generated_contracts LIMIT 5")
            all_contracts = cursor.fetchall()
            logger.info(f"Available contracts in DB: {all_contracts}")
            return

        if contract['status'] in {'completed', 'processing'}:
            conn.rollback()
            return {"status": contract['status'], "duplicate": True}
        cursor.execute("""UPDATE generated_contracts SET status='processing', error_message=NULL,
                          generation_started_at=CURRENT_TIMESTAMP WHERE id=%(id)s""", {"id": contract_uuid})
        conn.commit()
        
        logger.info("Contrato encontrado: %s", contract['title'])

        gen_user_id = str(contract['user_id'])
        gen_title = contract['title'] or "Contrato"
        safe_notification(
            user_id=gen_user_id,
            title="Generación iniciada",
            message=f"Se ha iniciado la generación del contrato '{gen_title}'.",
            notification_type="info",
            related_entity_type="generated_contract",
            related_entity_id=contract_id
        )

        details = contract['contract_details']
        contract_type = require_supported_contract_type(contract['contract_type'])['id']
        tone = contract.get('tone', 'Legal Formal')

        logger.info("Generando contenido para %s (tono: %s)...", contract_type, tone)
        generated_content = generate_contract_content(contract_type, details, tone=tone)
        validation = validate_generated_draft(generated_content, contract_type)
        if not validation.valid:
            logger.warning("Regenerando borrador inválido para %s: %s", contract_id, validation.errors)
            generated_content = generate_contract_content(contract_type, details)
            validation = validate_generated_draft(generated_content, contract_type)
            if not validation.valid:
                raise ValueError("Borrador inválido: " + "; ".join(validation.errors))
        
        _, completed_now = complete_generation(
            str(contract_uuid), generated_content, GENERATION_PROMPT_VERSION, settings.openai_model
        )
        logger.info("Contrato %s generado exitosamente", contract_id)

        safe_notification(
            user_id=gen_user_id,
            title="Contrato generado",
            message=f"El contrato '{gen_title}' se ha generado correctamente.",
            notification_type="success",
            related_entity_type="generated_contract",
            related_entity_id=contract_id
        )

    except Exception as e:
        logger.error("Error generando contrato %s: %s", contract_id, e, exc_info=True)

        if 'gen_user_id' in locals() and gen_user_id:
            error_gen_title = locals().get('gen_title', 'Contrato')
            safe_notification(
                user_id=gen_user_id,
                title="Error en la generación",
                message=f"Ha ocurrido un error al generar el contrato '{error_gen_title}'. Por favor, inténtalo de nuevo.",
                notification_type="error",
                related_entity_type="generated_contract",
                related_entity_id=contract_id
            )

        if conn:
            try:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute("""UPDATE generated_contracts SET status='error', error_message=%(message)s,
                                  generation_finished_at=CURRENT_TIMESTAMP WHERE id=%(id)s""",
                               {"id": contract_uuid, "message": str(e).replace("\n", " ")[:1000]})
                conn.commit()
            except Exception as _upd_err:
                logger.warning("No se pudo actualizar el estado de error del contrato %s: %s", contract_uuid, _upd_err)
        raise e
    finally:
        if conn:
            release_connection(conn)

