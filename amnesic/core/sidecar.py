from typing import Dict, Any, Optional
import threading

import os
import json
import threading
import logging
from typing import Dict, Any, Optional, List, Tuple
from ..tools.ast_mapper import StructuralMapper
from ..tools.vector_store import VectorStore

logger = logging.getLogger("amnesic.sidecar")

class SharedSidecar:
    """
    A persistent, thread-safe shared brain for the Amnesic Protocol.
    Supports Hybrid Indexing: Vector (Semantic) + AST (Structural).
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, driver=None, cache_dir: str = ".amnesic_cache"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SharedSidecar, cls).__new__(cls)
                    cls._instance.cache_dir = cache_dir
                    cls._instance.cache_file = os.path.join(cache_dir, "brain.json")
                    cls._instance.knowledge_graph = {}
                    cls._instance.vector_store = VectorStore(driver=driver)
                    cls._instance._load_from_disk()
        return cls._instance

    def ingest_knowledge(self, key: str, value: str, type: str = "text_content", metadata: Dict = None):
        """
        Add a fact to the shared brain and index it both semantically and structurally.
        """
        with self._lock:
            # 1. Store raw content
            self.knowledge_graph[key] = {
                "value": value,
                "type": type,
                "metadata": metadata or {}
            }
            
            # 2. Semantic Indexing (Vector)
            self.vector_store.add_document(doc_id=key, content=value, metadata=metadata)
            
            # 3. Structural Indexing (AST)
            # If the value looks like code, we try to parse it
            if type == "code_file" or "def " in value or "class " in value:
                try:
                    # Note: StructuralMapper usually scans disk, 
                    # but here we can use it to map individual snippets if needed.
                    # For now, we rely on the vector store for snippet retrieval
                    # and the main 'File Map' for structural disk navigation.
                    pass
                except Exception: pass

            self._save_to_disk()

    def query_semantic(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search offloaded context using fuzzy conceptual queries.
        """
        with self._lock:
            results = self.vector_store.search(query, top_k=top_k)
            output = []
            for doc_id, score in results:
                fact = self.knowledge_graph.get(doc_id)
                if fact:
                    output.append({
                        "key": doc_id,
                        "content": fact["value"],
                        "score": round(score, 3)
                    })
            return output

    def query_knowledge(self, key: str) -> Optional[Any]:
        """Direct lookup by exact symbolic key."""
        with self._lock:
            data = self.knowledge_graph.get(key)
            return data["value"] if data else None

    def delete_knowledge(self, key: str):
        with self._lock:
            if key in self.knowledge_graph:
                del self.knowledge_graph[key]
                self._save_to_disk()

    def get_all_knowledge(self) -> Dict[str, Any]:
        with self._lock:
            # Flatten for the Manager's 'Backpack' view
            return {k: v["value"] for k, v in self.knowledge_graph.items()}

    def _save_to_disk(self):
        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
            with open(self.cache_file, "w") as f:
                json.dump(self.knowledge_graph, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save brain to disk: {e}")

    def _load_from_disk(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r") as f:
                    self.knowledge_graph = json.load(f)
                    # Re-populate vector store for immediate use
                    for key, data in self.knowledge_graph.items():
                        self.vector_store.add_document(doc_id=key, content=data["value"], metadata=data.get("metadata"))
        except Exception as e:
            logger.error(f"Failed to load brain from disk: {e}")

    def reset(self):
        with self._lock:
            self.knowledge_graph = {}
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            self.vector_store = VectorStore()
