
import json
import logging
import os
import sys

from .build_rag_corpus import get_latest_corpus_path
from .qdrant_loader import QdrantLoader
from .utils import load_config, setup_logging


logger = logging.getLogger(__name__)


def _read_jsonl(path):
    with open(path, 'r', encoding='utf-8') as source:
        return [json.loads(line) for line in source if line.strip()]


def initialize_qdrant() -> bool:
    load_config()
    embedding_model = os.getenv(
        'OPENAI_EMBEDDING_MODEL',
        'text-embedding-3-small',
    )
    base_dir = get_latest_corpus_path()
    if not base_dir:
        logger.error('No se encontró ninguna versión del corpus legal')
        return False

    chunks_path = os.path.join(base_dir, 'chunks', 'chunks.jsonl')
    cache_path = os.path.join(base_dir, 'embeddings', 'embeddings_cache.jsonl')
    chunks = _read_jsonl(chunks_path)
    cache_records = _read_jsonl(cache_path)
    cache = {
        record['text_hash']: record['vector']
        for record in cache_records
        if record.get('embedding_model') == embedding_model
    }

    missing = [chunk['text_hash'] for chunk in chunks if chunk['text_hash'] not in cache]
    if missing:
        logger.error(
            'La caché RAG para %s está incompleta: faltan %s embeddings (%s)',
            embedding_model,
            len(missing),
            missing[:5],
        )
        return False

    embeddings = [cache[chunk['text_hash']] for chunk in chunks]
    if not embeddings:
        logger.error('El corpus RAG no contiene embeddings')
        return False

    collection_name = os.getenv('QDRANT_COLLECTION')
    if not collection_name:
        version_suffix = os.path.basename(base_dir).replace('-', '_')
        collection_name = f'legal_chunks_es_{version_suffix}'

    loader = QdrantLoader(collection_name, len(embeddings[0]))
    loader.ensure_collection()
    loader.upload_chunks(chunks, embeddings)
    count = loader.get_count()
    if count < len(chunks):
        logger.error(
            'Qdrant contiene %s puntos, pero se esperaban al menos %s',
            count,
            len(chunks),
        )
        return False

    logger.info(
        'Colección %s preparada offline con %s fragmentos usando %s',
        collection_name,
        len(chunks),
        embedding_model,
    )
    return True


if __name__ == '__main__':
    setup_logging()
    sys.exit(0 if initialize_qdrant() else 1)
