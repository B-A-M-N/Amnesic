import os
from typing import List, Dict, TypedDict

class TextChunk(TypedDict):
    source_file: str
    chunk_index: int
    content: str
    metadata: Dict

class TextMapper:
    def __init__(self, root_dir: str, ignore_dirs: List[str] = None):
        self.root_dir = root_dir
        self.ignore_dirs = ignore_dirs or [".git", "__pycache__", "venv", "node_modules", ".gemini", ".amnesic_cache"]
        self.extensions = [".md", ".txt", ".rst"]

    def scan_repository(self) -> List[TextChunk]:
        """
        Scans text files and chunks them for the VectorStore.
        """
        chunks = []
        
        for root, dirs, files in os.walk(self.root_dir):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                if any(file.endswith(ext) for ext in self.extensions):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    
                    file_chunks = self._process_file(full_path, rel_path)
                    chunks.extend(file_chunks)
                    
        return chunks

    def _process_file(self, full_path: str, rel_path: str) -> List[TextChunk]:
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple paragraph-based chunking for MVP
            # In production, use a sliding window or markdown-aware splitter
            raw_chunks = content.split("\n\n")
            
            structured_chunks = []
            for i, chunk in enumerate(raw_chunks):
                if len(chunk.strip()) > 50: # Ignore tiny chunks
                    structured_chunks.append({
                        "source_file": rel_path,
                        "chunk_index": i,
                        "content": chunk.strip(),
                        "metadata": {"source": rel_path, "type": "documentation"}
                    })
            return structured_chunks
            
        except Exception as e:
            print(f"[WARN] Could not read text file {rel_path}: {e}")
            return []
