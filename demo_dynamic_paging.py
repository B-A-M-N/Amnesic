import time
from amnesic.core.dynamic_pager import DynamicPager, DynamicPage
from amnesic.tools.vector_store import VectorStore

class MockDriver:
    def embed(self, text: str):
        # simple deterministic mock embedding
        val = len(text) / 100.0
        return [val, val] 

def main():
    print("=== DYNAMIC PAGER PROTOTYPE DEMO ===\n")

    # 1. Setup
    driver = MockDriver()
    vector_store = VectorStore(driver)
    pager = DynamicPager(capacity_tokens=100, vector_store=vector_store) # Small capacity to force eviction
    
    # 2. Add High Priority Page (e.g. Mission)
    print("--- 1. Pinned & High Priority ---")
    pager.pin_page("SYS:MISSION", "Mission: Build the Amnesic OS")
    print(f"L1 Usage: {pager.current_usage}/100")
    print(pager.render_context())
    
    # 3. Add Normal Pages
    print("\n--- 2. Filling L1 ---")
    # "Page A" (20 chars = ~5 tokens). Priority 5.
    pager.request_access("Page A", "Content of Page A...", priority=5)
    pager.tick()
    
    # "Page B" (20 chars = ~5 tokens). Priority 8 (High).
    pager.request_access("Page B", "Content of Page B...", priority=8)
    pager.tick()
    
    # "Page C" (20 chars = ~5 tokens). Priority 2 (Low).
    pager.request_access("Page C", "Content of Page C...", priority=2)
    pager.tick()
    
    print(f"Stats: {pager.get_stats()}")
    print("Pages in L1:", list(pager.l1_active.keys()))
    
    # 4. Trigger Eviction
    print("\n--- 3. Trigger Eviction (Adding Large Page) ---")
    # Add a large page that forces eviction. 
    # Capacity is 100.
    # Let's add 320 chars (80 tokens). 22 + 80 = 102. Eviction needed.
    
    large_content = "X" * 320
    print(f"Requesting Large Page D ({len(large_content)//4} tokens)...")
    pager.request_access("Page D", large_content, priority=6)
    
    print("Pages in L1:", list(pager.l1_active.keys()))
    print("Pages in L2:", list(pager.l2_staging.keys()))
    
    # Expected: 
    # Mission (Pinned) -> Stays
    # Page B (Pri 8, recent) -> Stays
    # Page D (Pri 6, new) -> Stays
    # Page A (Pri 5) -> Candidate?
    # Page C (Pri 2) -> Most likely victim
    
    # Let's verify scores:
    # A: Pri 5, LastAccess 1. Score = 50 + 1 = 51.
    # B: Pri 8, LastAccess 2. Score = 80 + 2 = 82.
    # C: Pri 2, LastAccess 3. Score = 20 + 3 = 23.
    # D needs space. C should go first.
    # If C goes, we free 5 tokens. Usage 22 - 5 = 17. 17 + 80 = 97. Fits!
    
    if "Page C" in pager.l2_staging:
        print("SUCCESS: Page C was evicted to L2.")
    else:
        print("FAILURE: Page C was NOT evicted.")

    # 5. Accessing L2 (Promotion)
    print("\n--- 4. Accessing Evicted Page (Promotion) ---")
    pager.tick()
    # Request C again. It should come back from L2 to L1.
    # This might force another eviction if D is still there.
    pager.request_access("Page C")
    
    print("Pages in L1:", list(pager.l1_active.keys()))
    print("Pages in L2:", list(pager.l2_staging.keys()))
    
    # D (80 toks) + Mission (7) + B (5) = 92.
    # Adding C (5) -> 97. Fits.
    # But wait, did we evict A?
    # When loading D (80), we had Mission(7)+A(5)+B(5)+C(5) = 22.
    # 22 - 5(C) = 17. 17 + 80 = 97.
    # So A, B, Mission, D are in L1.
    # Now requesting C (5). 97 + 5 = 102. Overflow.
    # Who gets evicted?
    # Mission (Pinned)
    # A: Pri 5, Access 1. Score 51.
    # B: Pri 8, Access 2. Score 82.
    # D: Pri 6, Access 4. Score 64.
    # C: Being promoted.
    # Victim should be A.
    
    if "Page A" in pager.l2_staging:
        print("SUCCESS: Page A was evicted to L2.")
    
    # 6. Archival to L3
    print("\n--- 5. Archiving to L3 ---")
    pager.archive_to_l3("Page A") # Currently in L2
    print(f"L3 Count: {len(pager.vector_store.documents)}")
    
    # 7. Recall from L3
    print("\n--- 6. Recall from L3 ---")
    recalled = pager.recall_from_l3("content", top_k=1)
    print(f"Recalled: {recalled}")
    print("Pages in L2:", list(pager.l2_staging.keys()))
    
    print("\n=== DEMO COMPLETE ===")

if __name__ == "__main__":
    main()
