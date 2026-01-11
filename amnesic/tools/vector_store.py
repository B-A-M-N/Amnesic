import math
import logging
from typing import List, Dict, TypedDict, Tuple

logger = logging.getLogger("amnesic.vector")

class VectorDoc(TypedDict):
    id: str
    content: str
    metadata: Dict
    embedding: List[float]

class VectorStore:
    def __init__(self, driver=None, embedding_fn=None):
        self.driver = driver
        self.embedding_fn = embedding_fn if embedding_fn else (lambda x: driver.embed(x) if driver else [])
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
        embedding = self.driver.embed(content)
        if embedding:
            self.collections[collection_name][doc_id] = {
                "id": doc_id,
                "content": content,
                "metadata": metadata or {},
                "embedding": embedding
            }

    def search(self, query: str, collection_name: str = "text", top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Returns [(doc_id, score), ...] sorted by similarity (descending).
        Target specific collection ("code" or "text").
        """
        if collection_name not in self.collections:
            return []

        query_vec = self.driver.embed(query)
        if not query_vec:
            return []

        results = []
        target_collection = self.collections[collection_name]
        
        for doc_id, doc in target_collection.items():
            score = self._cosine_similarity(query_vec, doc["embedding"])
            results.append((doc_id, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Manual cosine similarity to avoid numpy dependency.
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
            
        return dot_product / (magnitude1 * magnitude2)
