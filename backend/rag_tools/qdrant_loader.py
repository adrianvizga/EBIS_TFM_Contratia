import logging
import os
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.http import models
from .utils import load_config

logger = logging.getLogger(__name__)

class QdrantLoader:

    def __init__(self, collection_name: str, vector_dim: int):
        load_config()
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY")
        
        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = collection_name
        self.vector_dim = vector_dim

    def ensure_collection(self, *, recreate: bool = False):
        try:
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            if exists and recreate:
                logger.info("Recreating candidate collection %s", self.collection_name)
                self.client.delete_collection(self.collection_name)
                exists = False
            
            if not exists:
                logger.info(f"Creating collection {self.collection_name} with dim {self.vector_dim}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_dim,
                        distance=models.Distance.COSINE
                    )
                )
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise

    def upload_chunks(self, chunks: List[Dict], embeddings: List[List[float]], batch_size=64):
        total = len(chunks)
        logger.info(f"Starting upload of {total} points to Qdrant...")
        
        for i in range(0, total, batch_size):
            batch_chunks = chunks[i:i+batch_size]
            batch_embeddings = embeddings[i:i+batch_size]
            
            points = []
            for chunk, vector in zip(batch_chunks, batch_embeddings):
                if vector is None:
                    continue
                
                payload = {key: value for key, value in chunk.items() if key != "vector"}
                
                import uuid
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["chunk_id"]))
                
                points.append(models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                ))
            
            if points:
                try:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )
                    logger.info(f"Uploaded batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}")
                except Exception as e:
                    logger.error(f"Error uploading batch: {e}")
                    raise

    def get_count(self) -> int:
        try:
            count_result = self.client.count(
                collection_name=self.collection_name,
                exact=True
            )
            return count_result.count
        except Exception as e:
            logger.error(f"Error getting count: {e}")
            return -1
