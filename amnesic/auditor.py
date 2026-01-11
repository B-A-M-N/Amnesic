import os
import pickle
from typing import List, Optional
from fastembed import TextEmbedding
import numpy as np

# --- THE AUDITOR (FastEmbed) ---
class Auditor:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", cache_dir: str = ".amnesic_cache"):
        self.embedder = TextEmbedding(model_name=model_name)
        self.goal_embedding = None
        self.cache_dir = cache_dir
        
        # Memory Stores
        self.file_paths: List[str] = []
        self.file_embeddings: List[np.ndarray] = []

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def set_goal(self, goal_text: str):
        self.goal_embedding = list(self.embedder.embed([goal_text]))[0]

    def check_drift(self, proposed_action: str) -> float:
        if self.goal_embedding is None:
            return 1.0
            
        action_embedding = list(self.embedder.embed([proposed_action]))[0]
        # Normalize for proper Cosine Similarity
        return np.dot(self.goal_embedding, action_embedding)

    def index_files(self, file_paths: List[str], force: bool = False):
        """Indexes files or loads from cache if available."""
        cache_file = os.path.join(self.cache_dir, "index.pkl")
        
        if os.path.exists(cache_file) and not force:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                self.file_paths = data['paths']
                self.file_embeddings = data['embeddings']
            return len(self.file_paths), True
        
        self.file_paths = file_paths
        self.file_embeddings = list(self.embedder.embed(file_paths))
        
        with open(cache_file, 'wb') as f:
            pickle.dump({'paths': self.file_paths, 'embeddings': self.file_embeddings}, f)
            
        return len(self.file_paths), False

    def get_relevant_files(self, query: str, top_k: int = 15) -> List[str]:
        if not self.file_paths:
            return []

        query_embedding = list(self.embedder.embed([query]))[0]
        scores = [np.dot(query_embedding, doc_emb) for doc_emb in self.file_embeddings]
        ranked = sorted(zip(scores, self.file_paths), key=lambda x: x[0], reverse=True)
        return [path for _, path in ranked[:top_k]]