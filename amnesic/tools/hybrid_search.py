from typing import List, Dict, Optional, Any
import logging
from .vector_store import VectorStore
from .ast_mapper import StructuralMapper
from .text_mapper import TextMapper

logger = logging.getLogger("amnesic.hybrid_search")

class HybridSearcher:
    def __init__(self, root_dir: str, driver):
        self.root_dir = root_dir
        self.driver = driver
        self.mapper = StructuralMapper(root_dir)
        self.text_mapper = TextMapper(root_dir)
        self.vector_store = VectorStore(driver)
        self.is_indexed = False
        self.code_map = []

    def index(self):
        """
        Builds both the AST map and Dual Vector Indices (Code + Text).
        """
        logger.info("Starting Dual-Embedding Indexing...")
        
        # 1. Pipeline A: Code (AST + Signatures)
        self.code_map = self.mapper.scan_repository()
        indexable_code = self.mapper.to_indexable_nodes(self.code_map)
        
        for node in indexable_code:
            self.vector_store.add_document(
                doc_id=node["id"],
                content=node["content"],
                metadata=node["metadata"],
                collection_name="code"
            )
        
        # 2. Pipeline B: Text (Documentation / Markdown)
        text_chunks = self.text_mapper.scan_repository()
        for chunk in text_chunks:
            doc_id = f"{chunk['source_file']}#chunk{chunk['chunk_index']}"
            self.vector_store.add_document(
                doc_id=doc_id,
                content=chunk["content"],
                metadata=chunk["metadata"],
                collection_name="text"
            )
            
        self.is_indexed = True
        logger.info(f"Indexing Complete: {len(indexable_code)} code nodes, {len(text_chunks)} text chunks.")

    def search(self, query: str, top_k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """
        Performs search across both Code and Text indices.
        """
        if not self.is_indexed:
            self.index()

        code_results = self.vector_store.search(query, collection_name="code", top_k=top_k)
        text_results = self.vector_store.search(query, collection_name="text", top_k=top_k)
        
        return {
            "code": [{"id": r[0], "score": r[1]} for r in code_results],
            "text": [{"id": r[0], "score": r[1]} for r in text_results]
        }
