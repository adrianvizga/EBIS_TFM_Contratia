
import argparse
import os
import json
import logging
from glob import glob
from .utils import setup_logging, load_config
from .chunker import LegalChunker
from .embedder import Embedder
from .qdrant_loader import QdrantLoader
from .corpus_integrity import assert_corpus_integrity

logger = logging.getLogger(__name__)

def get_latest_corpus_path():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "legal_corpus", "es")
    versions = sorted(glob(os.path.join(base_dir, "v[0-9]*_*")))
    return versions[-1] if versions else None

def load_manifest(base_dir: str):
    manifest_path = os.path.join(base_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        logger.error(f"Manifest not found at {manifest_path}")
        return None
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description="Build RAG Corpus")
    parser.add_argument("--stage", choices=["chunks", "embeddings", "qdrant", "all"], required=True)
    parser.add_argument("--version", help="Specific version folder name (e.g. v1_2026-02-14)")
    parser.add_argument("--dry-run", action="store_true", help="Do not call OpenAI or Qdrant")
    args = parser.parse_args()

    setup_logging()
    load_config()

    if args.version:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "legal_corpus", "es", args.version)
    else:
        base_dir = get_latest_corpus_path()
        if not base_dir:
            logger.error("No corpus version found!")
            return

    logger.info(f"Using corpus at: {base_dir}")
    
    manifest = load_manifest(base_dir)
    if not manifest:
        raise SystemExit(1)
    try:
        assert_corpus_integrity(base_dir, validate_chunks=False)
    except ValueError as error:
        logger.error("%s", error)
        raise SystemExit(1) from error

    chunks_dir = os.path.join(base_dir, "chunks")
    embeddings_dir = os.path.join(base_dir, "embeddings")
    os.makedirs(chunks_dir, exist_ok=True)
    os.makedirs(embeddings_dir, exist_ok=True)

    chunks_file = os.path.join(chunks_dir, "chunks.jsonl")
    stats_file = os.path.join(chunks_dir, "chunks_stats.json")
    preview_file = os.path.join(chunks_dir, "chunks_preview.md")
    
    embeddings_cache_file = os.path.join(embeddings_dir, "embeddings_cache.jsonl")
    embeddings_stats_file = os.path.join(embeddings_dir, "embeddings_stats.json")

    if args.stage in ["chunks", "all"]:
        logger.info("Generando chunks del corpus legal")
        chunker = LegalChunker(
            chunk_max_tokens=int(os.getenv("CHUNK_MAX_TOKENS", 900)),
            chunk_min_tokens=int(os.getenv("CHUNK_MIN_TOKENS", 250))
        )
        
        normalized_dir = os.path.join(base_dir, "normalized")
        all_chunks = []
        chunk_stats = {"total": 0, "by_law": {}}
        
        for doc in manifest["documents"]:
            law_key = doc["law_key"]
            norm_path_rel = doc["files"]["normalized_path"]
            file_path = os.path.join(base_dir, norm_path_rel)
            
            if not os.path.exists(file_path):
                logger.warning(f"File not found for key {law_key}: {file_path}")
                continue
            
            logger.info(f"Processing {law_key} from {file_path}")
            
            extra_meta = {
                "doc_version": manifest["version"],
                "jurisdiction": manifest["jurisdiction"],
                "language": manifest["language"],
                "law_name": doc["law_name"],
                "official_id": doc.get("official_id") or doc.get("boe_id"),
                "provider": doc.get("provider", "boe"),
                "citation_prefix": doc.get("citation_prefix", law_key),
                "legal_scope": doc.get("scope", manifest["jurisdiction"]),
                "consolidated_at": doc["source"].get("consolidated_at"),
                "topics": doc.get("topics", []),
                "subjects": doc.get("subjects", []),
                "contract_phases": doc.get("contract_phases", []),
                "include_article_ranges": doc.get("extraction", {}).get("include_article_ranges", []),
                "source_url": doc["source"].get("url"),
                "retrieved_at": doc["source"].get("retrieved_at")
            }
            
            file_chunks = 0
            for chunk in chunker.chunk_file(file_path, law_key, extra_meta):
                all_chunks.append(chunk)
                file_chunks += 1
            
            chunk_stats["by_law"][law_key] = chunk_stats["by_law"].get(law_key, 0) + file_chunks
            
        chunk_stats["total"] = len(all_chunks)
        
        with open(chunks_file, 'w', encoding='utf-8') as f:
            for c in all_chunks:
                f.write(json.dumps(c) + "\n")
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(chunk_stats, f, indent=2)
            
        with open(preview_file, 'w', encoding='utf-8') as f:
            f.write("# Chunks Preview\n\n")
            for i, c in enumerate(all_chunks[:20]):
                f.write(f"## Chunk {i+1} ({c['chunk_id']})\n")
                f.write(f"**Citation:** {c['citation']}\n")
                f.write(f"**Metadata:** {c['law_key']} | {c.get('source_url')}\n\n")
                f.write(f"```text\n{c['text'][:500]}...\n```\n\n")
        
        logger.info(f"Chunks generated: {chunk_stats['total']}")

    if args.stage in ["embeddings", "all"]:
        logger.info("Generando embeddings")
        
        if 'all_chunks' not in locals():
            all_chunks = []
            if os.path.exists(chunks_file):
                with open(chunks_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        all_chunks.append(json.loads(line))
            else:
                logger.error("Chunks file not found!")
                return

        if args.dry_run:
            logger.info("Dry run: Skipping OpenAI calls")
            embeddings = [None] * len(all_chunks)
            with open(embeddings_stats_file, 'w', encoding='utf-8') as f:
                json.dump({"dry_run": True}, f, indent=2)
        else:
            embedder = Embedder(cache_file=embeddings_cache_file)
            embeddings = embedder.get_embeddings(all_chunks)
            
            stats = embedder.get_stats()
            logger.info(f"Embeddings stats: {stats}")
            with open(embeddings_stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)

    if args.stage in ["qdrant", "all"]:
        logger.info("Cargando vectores en Qdrant")
        
        if args.dry_run:
            logger.info("Dry run: Skipping Qdrant upload")
            return

        if 'all_chunks' not in locals():
             all_chunks = []
             with open(chunks_file, 'r', encoding='utf-8') as f:
                for line in f:
                    all_chunks.append(json.loads(line))
             
             embedder = Embedder(cache_file=embeddings_cache_file)
             embeddings = embedder.get_embeddings(all_chunks) 

        collection_name = os.getenv("QDRANT_COLLECTION")
        if not collection_name:
            version_suffix = os.path.basename(base_dir).replace("-", "_") 
            collection_name = f"legal_chunks_es_{version_suffix}"
        expected_collection = f"legal_chunks_es_{os.path.basename(base_dir).replace('-', '_')}"
        if collection_name != expected_collection:
            raise RuntimeError(f"La colección candidata debe ser {expected_collection}, no {collection_name}")
        
        vector_dim = 1536
        for v in embeddings:
            if v:
                vector_dim = len(v)
                break
        
        qdrant = QdrantLoader(collection_name, vector_dim)
        qdrant.ensure_collection(recreate=True)
        
        logger.info("Cleaning up old law keys (LAU, CC)...")
        try:
            from qdrant_client.http import models
            qdrant.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="law_key",
                                match=models.MatchAny(any=["LAU", "CC"])
                            )
                        ]
                    )
                )
            )
            logger.info("Cleanup successful")
        except Exception as e:
            logger.warning(f"Cleanup failed (might be first run or not supported): {e}")

        qdrant.upload_chunks(all_chunks, embeddings)
        
        count = qdrant.get_count()
        logger.info(f"Total points in collection {collection_name}: {count}")

if __name__ == "__main__":
    main()
