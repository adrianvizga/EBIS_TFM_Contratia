
import logging
import os
import re
import unicodedata
import warnings
from typing import List, Dict, Any, Optional
from glob import glob

warnings.filterwarnings("ignore", message="Api key is used with an insecure connection", category=UserWarning)
from services.contract_context import ContractContext, coerce_contract_context

logger = logging.getLogger(__name__)


def _terms(text: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    stop = {"para", "como", "entre", "sobre", "antes", "debe", "puede", "contrato", "servicios", "articulo"}
    return {term for term in re.findall(r"[a-z0-9]+", plain) if len(term) > 3 and term not in stop}


def _requires_scope_abstention(text: str, context: ContractContext) -> bool:
    plain = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    if re.search(r"\b(homicidio|prision|delito|pena penal)\b", plain):
        return True
    if context.regulated_sector and re.search(r"\b(regulatorios especificos|autorizar|autorizacion|licencia sectorial)\b", plain):
        return True
    return False


def _get_collection_name() -> str:
    from core.config import settings
    if settings.qdrant_collection:
        logger.debug("Qdrant collection (config): %s", settings.qdrant_collection)
        return settings.qdrant_collection

    base_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "legal_corpus", "es"
    )
    versions = sorted(glob(os.path.join(base_dir, "v[0-9]*_*")))
    if versions:
        version_suffix = os.path.basename(versions[-1]).replace("-", "_")
        return f"legal_chunks_es_{version_suffix}"
    return "legal_chunks_es"


def _get_qdrant_client():
    from core.config import settings
    from qdrant_client import QdrantClient
    logger.debug("Conectando a Qdrant: %s", settings.qdrant_url)
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None
    )


def _get_query_embedding(text: str) -> List[float]:
    from core.config import settings
    from openai import OpenAI
    if os.name == "nt":
        try:
            import truststore
            truststore.inject_into_ssl()
        except ImportError:
            pass

    logger.debug("Generando embedding para query (len=%d)", len(text))
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        input=text,
        model=settings.openai_embedding_model,
    )
    return response.data[0].embedding


def retrieve_legal_context(
    clause_text: str,
    contract_type: str = "",
    top_k: int = 5,
    score_threshold: Optional[float] = None,
    strict: bool = False,
    context: ContractContext | dict | None = None,
) -> List[Dict[str, Any]]:
    try:
        from core.config import settings
        collection_name = _get_collection_name()
        client = _get_qdrant_client()
        query_vector = _get_query_embedding(clause_text[:2000])

        law_key_filter = None
        if contract_type in ("arrendamiento_vivienda", "arrendamiento_local"):
            from qdrant_client.http import models
            law_key_filter = models.Filter(
                should=[
                    models.FieldCondition(
                        key="law_key",
                        match=models.MatchValue(value="LAU_1994")
                    ),
                    models.FieldCondition(
                        key="law_key",
                        match=models.MatchValue(value="CC_ES")
                    )
                ]
            )

        contract_context = coerce_contract_context(context, clause_text, contract_type)
        if _requires_scope_abstention(clause_text, contract_context):
            logger.info("RAG: abstención por consulta fuera de la cobertura general")
            return []
        query_terms = _terms(clause_text)
        candidate_limit = max(top_k, top_k * 8 if contract_type == "prestacion_servicios" else top_k)
        results = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=law_key_filter,
            limit=candidate_limit,
            score_threshold=settings.rag_score_threshold if score_threshold is None else score_threshold,
        )

        candidates = []
        for hit in results.points:
            payload = hit.payload or {}
            law_key = payload.get("law_key", "")
            if contract_context.party_relation == "b2b" and law_key == "TRLGDCU_2007":
                continue
            if contract_context.party_relation == "b2c" and law_key == "MOROSIDAD_2004":
                continue
            topics = payload.get("topics", []) or []
            bonus = 0.0
            if contract_context.party_relation in topics:
                bonus += 0.03
            if contract_context.personal_data == "yes" and "privacy" in topics:
                bonus += 0.04
            if contract_context.intellectual_property == "yes" and "ip" in topics:
                bonus += 0.04
            article_number = str(payload.get("article_number", ""))
            plain_query = unicodedata.normalize("NFKD", clause_text).encode("ascii", "ignore").decode().lower()
            if contract_context.personal_data == "yes" and "encargado" in plain_query and law_key == "RGPD" and article_number == "28":
                bonus += 0.12
            if contract_context.channel == "distance" and "desistimiento" in plain_query and law_key == "TRLGDCU_2007" and article_number == "104":
                bonus += 0.12
            text_terms = _terms(payload.get("text", ""))
            lexical_overlap = len(query_terms & text_terms) / max(1, len(query_terms))
            bonus += min(0.10, lexical_overlap * 0.12)
            candidates.append({
                "chunk_id": payload.get("chunk_id", ""),
                "citation": payload.get("citation", ""),
                "law_name": payload.get("law_name", ""),
                "law_key": payload.get("law_key", ""),
                "article_number": payload.get("article_number", ""),
                "text": payload.get("text", ""),
                "text_hash": payload.get("text_hash", ""),
                "doc_version": payload.get("doc_version", ""),
                "official_id": payload.get("official_id", ""),
                "topics": topics,
                "subjects": payload.get("subjects", []) or [],
                "contract_phases": payload.get("contract_phases", []) or [],
                "source_url": payload.get("source_url", ""),
                "score": round(hit.score, 4),
                "ranking_score": round(hit.score + bonus, 4),
                "applicability_warning": contract_context.party_relation == "unknown" and law_key in {"TRLGDCU_2007", "MOROSIDAD_2004"},
                "out_of_scope_sector": contract_context.regulated_sector,
            })

        candidates.sort(key=lambda item: item["ranking_score"], reverse=True)
        selected: list[dict[str, Any]] = []
        law_counts: dict[str, int] = {}
        for item in candidates:
            if law_counts.get(item["law_key"], 0) >= max(2, top_k // 2):
                continue
            selected.append(item)
            law_counts[item["law_key"]] = law_counts.get(item["law_key"], 0) + 1
            if len(selected) == top_k:
                break

        logger.info(f"RAG: Retrieved {len(selected)} legal fragments (collection={collection_name})")
        return selected

    except Exception as e:
        if strict:
            raise RuntimeError("RAG retrieval failed") from e
        logger.warning(f"RAG retrieval failed (non-blocking): {e}")
        return []


def build_grounded_answer(context: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not context:
        return {
            "answer": "No se ha encontrado respaldo suficiente en el corpus legal disponible.",
            "citations": [],
            "abstained": True,
        }
    excerpts = []
    citations = []
    for item in context:
        citation = item.get("citation", "").strip()
        text = item.get("text", "").strip()
        excerpts.append(f"[{citation}] {text}")
        citations.append(citation)
    return {"answer": "\n\n".join(excerpts), "citations": citations, "abstained": False}


def format_legal_context_for_prompt(context: List[Dict[str, Any]]) -> str:
    if not context:
        return ""

    lines = ["CONTEXTO LEGAL (artículos relevantes recuperados del corpus):\n"]
    sectors = {item.get("out_of_scope_sector") for item in context if item.get("out_of_scope_sector")}
    if sectors:
        lines.append("ADVERTENCIA: se ha detectado un posible sector regulado fuera de la cobertura general; limita las conclusiones y recomienda revisión especializada.\n")
    if any(item.get("applicability_warning") for item in context):
        lines.append("ADVERTENCIA: no hay datos suficientes para decidir si el régimen B2B o B2C resulta aplicable.\n")
    for i, item in enumerate(context, 1):
        lines.append(f"[{i}] {item['citation']} ({item['law_name']}):")
        text_preview = item["text"][:600].strip()
        lines.append(f"{text_preview}\n")

    return "\n".join(lines)
