import time
import os
from amnesic.tools.ast_mapper import StructuralMapper
from fastembed import TextEmbedding

def profile_overhead():
    print("--- Amnesic Kernel Overhead Profile ---")
    
    # 1. Profile Embedding
    print("Testing Local Embedding (FastEmbed)...")
    start = time.time()
    embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    print(f"  Embedder Load: {time.time() - start:.2f}s")
    
    start = time.time()
    list(embedder.embed(["This is a test action to check relevance for the mission."]))
    print(f"  Single Embedding Latency: {time.time() - start:.2f}s")

    # 2. Profile AST Mapping
    print("\nTesting AST Mapping (StructuralMapper)...")
    # Simulate a directory with some files
    rd = "."
    mapper = StructuralMapper(root_dir=rd)
    start = time.time()
    repo_map = mapper.scan_repository()
    print(f"  Scan Repository ({len(repo_map)} files): {time.time() - start:.2f}s")

    # 3. Profile Token Counting
    import tiktoken
    print("\nTesting Token Counting (tiktoken)...")
    enc = tiktoken.get_encoding("cl100k_base")
    heavy_text = "This is some hex noise. " * 1000
    start = time.time()
    enc.encode(heavy_text)
    print(f"  Tokenizing 10k chars: {time.time() - start:.4f}s")

if __name__ == "__main__":
    profile_overhead()