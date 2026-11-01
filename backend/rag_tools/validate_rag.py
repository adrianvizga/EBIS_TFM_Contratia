
import argparse
import json
import logging
import os
from pathlib import Path

from .build_rag_corpus import get_latest_corpus_path
from .corpus_integrity import validate_corpus_integrity
from .evaluate_rag import evaluate
from .qdrant_loader import QdrantLoader
from .utils import load_config, setup_logging

logger = logging.getLogger(__name__)


def validate_pipeline(version=None) -> bool:
    setup_logging()
    load_config()
    base_dir = Path(get_latest_corpus_path()) if not version else Path(__file__).resolve().parents[1] / "legal_corpus" / "es" / version
    if not base_dir.is_dir():
        logger.error("Corpus version not found: %s", base_dir)
        return False

    errors = validate_corpus_integrity(base_dir)
    if errors:
        for error in errors:
            logger.error("Corpus integrity: %s", error)
        return False

    try:
        chunks = [json.loads(line) for line in (base_dir / "chunks" / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError, KeyError) as error:
        logger.error("Could not load chunks: %s", error)
        return False
    ids = [chunk.get("chunk_id") for chunk in chunks]
    if not chunks or None in ids or len(ids) != len(set(ids)):
        logger.error("Chunks are empty, unidentified or duplicated")
        return False
    expected_laws = {document["law_key"] for document in json.loads((base_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]}
    actual_laws = {chunk.get("law_key") for chunk in chunks}
    if actual_laws != expected_laws:
        logger.error("Law keys mismatch: expected=%s actual=%s", expected_laws, actual_laws)
        return False
    required = ("doc_version", "jurisdiction", "language", "source_url", "text_hash", "citation")
    for chunk in chunks:
        missing = [field for field in required if not chunk.get(field)]
        if missing:
            logger.error("Chunk %s missing metadata: %s", chunk.get("chunk_id"), missing)
            return False

    cache_path = base_dir / "embeddings" / "embeddings_cache.jsonl"
    if not cache_path.is_file():
        logger.error("Embeddings cache missing: %s", cache_path)
        return False
    try:
        cache = [json.loads(line) for line in cache_path.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError) as error:
        logger.error("Invalid embeddings cache: %s", error)
        return False
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    cached_hashes = {item.get("text_hash") for item in cache if item.get("embedding_model") == model and item.get("vector")}
    missing_embeddings = [chunk["text_hash"] for chunk in chunks if chunk["text_hash"] not in cached_hashes]
    if missing_embeddings:
        logger.error("Missing embeddings: %s", missing_embeddings[:5])
        return False

    collection = os.getenv("QDRANT_COLLECTION") or f"legal_chunks_es_{base_dir.name.replace('-', '_')}"
    count = QdrantLoader(collection, 1).get_count()
    if count != len(chunks):
        logger.error("Qdrant/chunks mismatch: qdrant=%s chunks=%s", count, len(chunks))
        return False

    try:
        datasets = sorted((base_dir / "evaluations").glob("rag_eval_v*.json"))
        if not datasets:
            logger.error("RAG evaluation dataset missing")
            return False
        evaluation = evaluate(datasets[-1], base_dir)
    except Exception as error:
        logger.error("RAG evaluation failed: %s", error, exc_info=True)
        return False
    logger.info("RAG metrics: %s", evaluation["metrics"])
    if not evaluation["passed"]:
        logger.error("RAG thresholds failed: %s", evaluation["failures"])
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version")
    args = parser.parse_args()
    raise SystemExit(0 if validate_pipeline(args.version) else 1)
