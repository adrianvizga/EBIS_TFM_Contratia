import json
import os
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
from .utils import load_config

logger = logging.getLogger(__name__)

class Embedder:

    def __init__(self, cache_file: str, model: str | None = None):
        load_config()
        if sys.platform == "win32":
            try:
                import truststore
                truststore.inject_into_ssl()
            except ImportError:
                logger.warning("truststore no disponible; se usará el almacén CA predeterminado")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        )
        self.cache_file = cache_file
        self.cache: Dict[str, List[float]] = {}
        self.target_cache_hashes: set[str] = set()
        self.new_embeddings_count = 0
        self.cache_hits_count = 0
        
        self._load_cache()

    def _load_cache(self):
        cache_path = Path(self.cache_file)
        candidates = [cache_path]
        try:
            corpus_root = cache_path.parents[2]
            candidates.extend(sorted(corpus_root.glob("v*/embeddings/embeddings_cache.jsonl")))
        except IndexError:
            pass
        for candidate in dict.fromkeys(candidates):
            if not candidate.is_file():
                continue
            logger.info("Loading embeddings cache from %s", candidate)
            try:
                f = candidate.open('r', encoding='utf-8')
                for line in f:
                    if not line.strip(): continue
                    try:
                        record = json.loads(line)
                        if record.get("embedding_model") == self.model:
                            self.cache[record["text_hash"]] = record["vector"]
                            if candidate == cache_path:
                                self.target_cache_hashes.add(record["text_hash"])
                    except json.JSONDecodeError:
                        continue
                f.close()
            except Exception as e:
                logger.error("Error loading cache %s: %s", candidate, e)
        logger.info("Loaded %s reusable embeddings", len(self.cache))

    def save_cache_incrementally(self, new_records: List[Dict]):
        if not new_records:
            return
            
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        
        with open(self.cache_file, 'a', encoding='utf-8') as f:
            for record in new_records:
                f.write(json.dumps(record) + "\n")

    def get_embeddings(self, chunks: List[Dict]) -> List[List[float]]:
        results = []
        to_embed_indices = []
        to_embed_texts = []
        
        for idx, chunk in enumerate(chunks):
            text_hash = chunk["text_hash"]
            if text_hash in self.cache:
                results.append(self.cache[text_hash])
                self.cache_hits_count += 1
            else:
                results.append(None)
                to_embed_indices.append(idx)
                to_embed_texts.append(chunk["text"])
        
        if to_embed_texts:
            logger.info(f"Generating embeddings for {len(to_embed_texts)} chunks")
            try:
                batch_size = 128
                for start in range(0, len(to_embed_texts), batch_size):
                    batch_texts = to_embed_texts[start:start + batch_size]
                    batch_indices = to_embed_indices[start:start + batch_size]
                    response = self.client.embeddings.create(input=batch_texts, model=self.model)
                    new_cache_records = []
                    for data, original_idx in zip(response.data, batch_indices):
                        embedding = data.embedding
                        results[original_idx] = embedding
                        chunk_hash = chunks[original_idx]["text_hash"]
                        self.cache[chunk_hash] = embedding
                        new_cache_records.append({"text_hash": chunk_hash, "embedding_model": self.model, "vector": embedding})
                        self.new_embeddings_count += 1
                    self.save_cache_incrementally(new_cache_records)
                    logger.info("Embedded %s/%s new chunks", min(start + batch_size, len(to_embed_texts)), len(to_embed_texts))
                
            except Exception as e:
                logger.error(f"Error calling OpenAI Embeddings API: {e}")
                raise e

        target = Path(self.cache_file)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as output:
            for chunk, vector in zip(chunks, results):
                output.write(json.dumps({"text_hash": chunk["text_hash"], "embedding_model": self.model, "vector": vector}) + "\n")
        temporary.replace(target)
        self.target_cache_hashes = {chunk["text_hash"] for chunk in chunks}
        return results

    def get_stats(self):
        return {
            "model": self.model,
            "cache_hits": self.cache_hits_count,
            "new_embeddings": self.new_embeddings_count,
            "total_processed": self.cache_hits_count + self.new_embeddings_count
        }
