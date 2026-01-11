from typing import Dict, Any, Optional
import threading

class SharedSidecar:
    """
    A thread-safe shared state container for Multi-Agent Synchronization.
    Acts as the 'Hive Mind' backend.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SharedSidecar, cls).__new__(cls)
                    cls._instance.knowledge_graph = {}
                    cls._instance.vectors = {}
        return cls._instance

    def ingest_knowledge(self, key: str, value: Any):
        """Add a fact to the shared brain."""
        with self._lock:
            self.knowledge_graph[key] = value

    def query_knowledge(self, key: str) -> Optional[Any]:
        """Retrieve a fact from the shared brain."""
        with self._lock:
            return self.knowledge_graph.get(key)

    def delete_knowledge(self, key: str):
        """Remove a fact from the shared brain."""
        with self._lock:
            if key in self.knowledge_graph:
                del self.knowledge_graph[key]

    def get_all_knowledge(self) -> Dict[str, Any]:
        """Dump the entire brain state."""
        with self._lock:
            return self.knowledge_graph.copy()

    def reset(self):
        """Clear the brain (for testing)."""
        with self._lock:
            self.knowledge_graph = {}
            self.vectors = {}
