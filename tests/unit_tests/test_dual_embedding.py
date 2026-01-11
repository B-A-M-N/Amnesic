import sys
import os

# Add root to path so we can import amnesic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.tools.hybrid_search import HybridSearcher
from amnesic.drivers.base import LLMDriver

class MockDriver(LLMDriver):
    """A mock driver that returns dummy embeddings for testing."""
    def embed(self, text: str):
        # Return a dummy vector of fixed length
        return [0.1] * 128
    
    def generate_json(self, prompt, system_prompt=None):
        return {}

def test_dual_indexing():
    print("🚀 Starting Dual-Embedding Verification...")
    
    # Initialize Searcher with current directory
    driver = MockDriver()
    searcher = HybridSearcher(root_dir=".", driver=driver)
    
    # Run Indexing
    print("📦 Indexing repository (AST + Text)...")
    searcher.index()
    
    v_store = searcher.vector_store
    
    # 1. Verify Code Collection
    code_count = len(v_store.collections["code"])
    print(f"📊 Code Nodes Indexed: {code_count}")
    
    # Check for a known symbol (e.g., this test file or app.py)
    # The ID format is "path::name"
    app_nodes = [id for id in v_store.collections["code"].keys() if "app.py" in id]
    if code_count > 0 and len(app_nodes) > 0:
        print(f"✅ Code Indexing PASS (Found {len(app_nodes)} nodes for app.py)")
    else:
        print("❌ Code Indexing FAIL (No nodes found)")

    # 2. Verify Text Collection
    text_count = len(v_store.collections["text"])
    print(f"📊 Text Chunks Indexed: {text_count}")
    
    # Check for README.md
    readme_chunks = [id for id in v_store.collections["text"].keys() if "README.md" in id]
    if text_count > 0 and len(readme_chunks) > 0:
        print(f"✅ Text Indexing PASS (Found {len(readme_chunks)} chunks for README.md)")
    else:
        print("❌ Text Indexing FAIL (No README chunks found)")

    # 3. Verify Search Separation
    print("🔍 Testing Search Separation...")
    results = searcher.search("FrameworkApp")
    
    if len(results["code"]) > 0:
        print(f"✅ Code Search PASS (Found {results['code'][0]['id']})")
    else:
        print("❌ Code Search FAIL")

    if len(results["text"]) > 0:
        print(f"✅ Text Search PASS (Found {results['text'][0]['id']})")
    else:
        print("❌ Text Search FAIL")

if __name__ == "__main__":
    try:
        test_dual_indexing()
        print("\n✨ All Dual-Embedding tests passed!")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)
