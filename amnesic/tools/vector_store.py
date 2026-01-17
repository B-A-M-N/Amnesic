import math
import logging
from typing import List, Dict, TypedDict, Tuple
from fastembed import TextEmbedding
import numpy as np

logger = logging.getLogger("amnesic.vector")

class VectorDoc(TypedDict):
    id: str
    content: str
    metadata: Dict
    embedding: List[float]

class VectorStore:
    def __init__(self, driver=None, embedding_fn=None):
        # We now ignore the driver for embeddings and use fastembed directly
        self.embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        
        # Storage: {"code": {doc_id: VectorDoc}, "text": {doc_id: VectorDoc}}
        self.collections: Dict[str, Dict[str, VectorDoc]] = {
            "code": {},
            "text": {}
        }

    def add_document(self, doc_id: str, content: str, metadata: Dict = None, collection_name: str = "text"):
        """Adds or updates a document in the specified collection."""
        if collection_name not in self.collections:
            self.collections[collection_name] = {}
            
        # Optimization: In a real DB, we'd check hash/timestamp before re-embedding
        embeddings = list(self.embedder.embed([content]))
        if embeddings:
            self.collections[collection_name][doc_id] = {
                "id": doc_id,
                "content": content,
                "metadata": metadata or {},
                "embedding": embeddings[0].tolist()
            }

    def search(self, query: str, collection_name: str = "text", top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Returns [(doc_id, score), ...] sorted by similarity (descending).
        Target specific collection ("code" or "text").
        """
        if collection_name not in self.collections:
            return []

        query_vecs = list(self.embedder.embed([query]))
        if not query_vecs:
            return []
        
        query_vec = query_vecs[0]

        results = []
        target_collection = self.collections[collection_name]
        
        for doc_id, doc in target_collection.items():
            score = self._cosine_similarity(query_vec, np.array(doc["embedding"]))
            results.append((doc_id, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Cosine similarity using numpy for efficiency.
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(dot_product / (norm1 * norm2))
