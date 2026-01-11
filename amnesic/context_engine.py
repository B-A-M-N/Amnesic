import os
from typing import List, Dict, Any, Literal, Union
from .tools.ast_mapper import StructuralMapper
from .tools.vector_store import VectorStore

class ContextEngine:
    def __init__(self, root_dir: str, driver):
        self.root_dir = root_dir
        self.driver = driver
        
        # Sub-Engines
        self.code_mapper = StructuralMapper(root_dir)
        self.vector_store = VectorStore(driver)
        
        # State
        self.indexed_files = set()

    def scan(self):
        """
        Scans the directory.
        - Updates AST for .py files.
        - Updates Vector Embeddings for Text files (.md, .txt, etc).
        """
        # 1. Update AST (Cheap)
        code_map = self.code_mapper.scan_repository()
        
        # 2. Update Vectors (Expensive - simplified for MVP)
        # We only look for typical text files
        text_extensions = {'.md', '.txt', '.rst', '.json', '.yaml', '.yml'}
        
        for root, dirs, files in os.walk(self.root_dir):
            if ".git" in dirs: dirs.remove(".git")
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in text_extensions:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    
                    # In a real system, check hash before re-embedding
                    if rel_path not in self.indexed_files:
                        try:
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            
                            # Chunking? For MVP, one file = one chunk.
                            # Qwen-3B handles ~32k context, so small files are fine.
                            self.vector_store.add_document(
                                doc_id=rel_path,
                                content=content,
                                metadata={"type": "text"}
                            )
                            self.indexed_files.add(rel_path)
                        except Exception as e:
                            print(f"Skipping {rel_path}: {e}")
        
        return code_map

    def search_text(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Performs vector search on text documents.
        Returns list of {path, score, preview}.
        """
        results = self.vector_store.search(query, top_k)
        output = []
        for doc_id, score in results:
            doc = self.vector_store.documents[doc_id]
            # Create a preview
            preview = doc["content"][:200].replace("\n", " ") + "..."
            output.append({
                "path": doc_id,
                "score": round(score, 3),
                "preview": preview
            })
        return output
