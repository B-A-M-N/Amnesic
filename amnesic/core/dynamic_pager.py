import logging
from typing import Dict, Optional, TypedDict, List
from pydantic import BaseModel
from amnesic.tools.vector_store import VectorStore
import tiktoken

logger = logging.getLogger("amnesic.dynamic_pager")

# Global Tokenizer Initialization
try:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except Exception as e:
    logger.warning(f"Tiktoken failed to load cl100k_base: {e}. Falling back to heuristic.")
    TOKENIZER = None

def count_tokens(text: str) -> int:
    """Accurate token counting using tiktoken (cl100k_base) with heuristic fallback."""
    if not text or len(text.strip()) == 0:
        return 0
    res = 0
    if TOKENIZER:
        try:
            # Add 75% safety margin for tokenizer mismatches (e.g. Qwen vs cl100k)
            # and to ensure ample headroom for system prompts.
            res = int(len(TOKENIZER.encode(text)) * 1.75)
        except Exception:
            pass
    
    if res == 0:
        # Fallback: Conservative estimate (chars / 3.0)
        res = int(len(text) / 3.0)
    
    # Ensure at least 1 token if text exists and is not whitespace
    return max(res, 1)

class DynamicPage(BaseModel):
    id: str
    content: str
    tokens: int
    last_accessed: int
    priority: int = 5  # 0-10, 10 is highest. 
    pinned: bool = False
    ttl: int = 10
    
class PagingStats(TypedDict):
    l1_used: int
    l1_capacity: int
    l1_count: int
    l2_count: int
    l3_count: int

class DynamicPager:
    def __init__(self, capacity_tokens: int = 32768, vector_store: Optional[VectorStore] = None):
        """
        Hierarchical Memory Management Unit.
        L1: Active Context (RAM, Token Limited)
        L2: Staging/Swap (RAM, Unlimited/High Limit)
        L3: Archival (Vector Database, Semantic Retrieval)
        """
        self.capacity = capacity_tokens
        self.vector_store = vector_store
        
        self.l1_active: Dict[str, DynamicPage] = {}
        self.l2_staging: Dict[str, DynamicPage] = {} 
        
        self.current_turn = 0

    def tick(self):
        """
        Maintenance cycle: Enforces turn-based TTL and dynamic capacity limits.
        Triggers 'Shifting' (Eviction to L2) if the workbench is saturated.
        """
        self.current_turn += 1
        for page_id in list(self.active_pages.keys()):
            page = self.active_pages[page_id]
            if page.pinned: continue # Pinned pages never die
            
            page.ttl -= 1
            if page.ttl <= 0:
                print(f"         Kernel: TTL Eviction - {page_id} shifting to L2.")
                self.evict_to_l2(page_id)

        # CAPACITY GOVERNANCE: Shift files to L2 if total usage > dynamic capacity
        # This preserves the 'Reasoning Floor' Turn-by-Turn
        current_usage = self.current_usage
        if current_usage > self.capacity:
            print(f"         Kernel: Workbench Saturated ({current_usage} > {self.capacity}). Shifting oldest evidence to L2...")
            # Sort active pages by priority then last_used (LRU)
            candidates = sorted(
                [p for p in self.active_pages.values() if not p.pinned],
                key=lambda x: (x.priority, x.last_accessed)
            )
            
            while self.current_usage > self.capacity and candidates:
                target = candidates.pop(0)
                self.evict_to_l2(target.id)
                print(f"         Kernel: Shifted {target.id} to L2.")

    def pin_page(self, page_id: str, content: str):
        """Loads a page that cannot be evicted."""
        self._load_page(page_id, content, priority=10, pinned=True)

    def _load_page(self, page_id: str, content: str, priority: int, pinned: bool):
        """Internal load helper."""
        tokens = count_tokens(content)
        new_page = DynamicPage(
            id=page_id,
            content=content,
            tokens=tokens,
            last_accessed=self.current_turn,
            priority=priority,
            pinned=pinned
        )
        self._promote_to_l1(new_page)

    def request_access(self, page_id: str, content: Optional[str] = None, priority: int = 5) -> bool:
        """
        Requests access to a page.
        1. Checks L1 (Hot)
        2. Checks L2 (Staging) -> Promotes to L1
        3. Checks L3 (Archive) -> Promotes to L1 [Not Implemented Automatically, needs explicit recall usually]
        4. Creates New if content provided
        """
        # 1. L1 Hit
        if page_id in self.l1_active:
            page = self.l1_active[page_id]
            page.last_accessed = self.current_turn
            page.ttl = 10
            # Update priority if explicitly requested with higher
            if priority > page.priority:
                page.priority = priority
            # REFRESH CONTENT if provided (Crucial for edit_file/write_file synchronization)
            if content:
                page.content = content
                page.tokens = count_tokens(content)
            return True

        # 2. L2 Hit (Promote)
        if page_id in self.l2_staging:
            page = self.l2_staging.pop(page_id)
            page.last_accessed = self.current_turn
            page.ttl = 10
            page.priority = max(page.priority, priority)
            
            # Update content if provided (refresh)
            if content:
                page.content = content
                page.tokens = count_tokens(content)
                
            return self._promote_to_l1(page)

        # 3. New Page
        if content:
            tokens = count_tokens(content)
            new_page = DynamicPage(
                id=page_id,
                content=content,
                tokens=tokens,
                last_accessed=self.current_turn,
                priority=priority,
                pinned=False
            )
            return self._promote_to_l1(new_page)

        logger.warning(f"PageFault: {page_id} not found in L1/L2 and no content provided.")
        return False

    def prefetch(self, page_id: str, content: str, priority: int = 3):
        """
        Loads a page into L2 (Staging) without promoting to L1.
        Useful for background loading anticipated resources.
        """
        # If already in L1, do nothing (it's already hot)
        if page_id in self.l1_active:
            return

        # If in L2, update it
        if page_id in self.l2_staging:
            page = self.l2_staging[page_id]
            page.content = content
            page.tokens = count_tokens(content)
            page.priority = max(page.priority, priority)
            page.last_accessed = self.current_turn
            logger.info(f"Prefetch update for {page_id} in L2.")
            return

        # Load into L2
        tokens = count_tokens(content)
        new_page = DynamicPage(
            id=page_id,
            content=content,
            tokens=tokens,
            last_accessed=self.current_turn,
            priority=priority,
            pinned=False
        )
        self.l2_staging[page_id] = new_page
        logger.info(f"Prefetched {page_id} to L2.")

    def evict_to_l2(self, page_id: str):
        """Explicitly moves a page from L1 to L2. Cannot evict pinned pages."""
        if page_id in self.l1_active:
            page = self.l1_active[page_id]
            if page.pinned:
                logger.warning(f"Eviction Blocked: {page_id} is PINNED.")
                return
            
            page = self.l1_active.pop(page_id)
            self.l2_staging[page_id] = page
            logger.info(f"Evicted {page_id} to L2.")

    def archive_to_l3(self, page_id: str):
        """Moves a page from L2 (or L1) to L3 (Vector Store)."""
        # Check L1 first
        if page_id in self.l1_active:
            self.evict_to_l2(page_id)
        
        # Check L2
        if page_id in self.l2_staging:
            page = self.l2_staging[page_id]
            if self.vector_store:
                self.vector_store.add_document(
                    doc_id=page.id,
                    content=page.content,
                    metadata={"priority": page.priority, "archived_at": self.current_turn}
                )
                del self.l2_staging[page_id]
                logger.info(f"Archived {page_id} to L3.")
            else:
                logger.warning("L3 unavailable (No VectorStore). Page remains in L2.")

    def recall_from_l3(self, query: str, top_k: int = 1) -> List[str]:
        """
        Semantic recall from L3. 
        Returns list of page_ids that were promoted to L2 (not L1 automatically to avoid thrashing).
        """
        if not self.vector_store:
            return []
            
        results = self.vector_store.search(query, top_k)
        recalled_ids = []
        for doc_id, score in results:
            doc = self.vector_store.documents.get(doc_id)
            if doc:
                # Reconstruct Page
                page = DynamicPage(
                    id=doc_id,
                    content=doc["content"],
                    tokens=count_tokens(doc["content"]),
                    last_accessed=self.current_turn,
                    priority=3, # Lower priority for recalled items until verified
                    pinned=False
                )
                self.l2_staging[doc_id] = page
                recalled_ids.append(doc_id)
        
        return recalled_ids

    def _promote_to_l1(self, page: DynamicPage) -> bool:
        """Attempts to add page to L1, triggering eviction if necessary."""
        if not self._make_space(page.tokens):
            logger.warning(f"OOM: Cannot load {page.id} ({page.tokens} toks). Page too large for L1.")
            # Put back in L2 if it was there or if we can't load it
            self.l2_staging[page.id] = page 
            return False
            
        self.l1_active[page.id] = page
        return True

    def _make_space(self, required_tokens: int) -> bool:
        """
        Smart Eviction Algorithm.
        Calculates an 'Eviction Score' for each page.
        Lowest Score = First to go.
        Score = (Recency_Weight * Recency) + (Priority_Weight * Priority)
        """
        # Safety check for impossible requests
        if required_tokens > self.capacity:
            return False

        while self.current_usage + required_tokens > self.capacity:
            candidates = [p for p in self.l1_active.values() if not p.pinned]
            
            if not candidates:
                return False 
            
            # Calculate Scores
            # Higher score = Keep. Lower score = Evict.
            # We want to keep recent items (High last_accessed)
            # We want to keep high priority items.
            
            # Normalize recency to avoid huge numbers if turns get high?
            # Simple addition is fine for now.
            
            # Heuristic: 1 Priority point is worth 5 turns of recency.
            scored_candidates = []
            for p in candidates:
                score = (p.priority * 10) + (p.last_accessed)
                scored_candidates.append((score, p))
            
            # Find victim (lowest score)
            victim = min(scored_candidates, key=lambda x: x[0])[1]
            
            self.evict_to_l2(victim.id)
            
        return True

    @property
    def current_usage(self) -> int:
        return sum(p.tokens for p in self.l1_active.values())

    @property
    def active_pages(self) -> Dict[str, DynamicPage]:
        """Backward compatibility for Pager.active_pages"""
        return self.l1_active

    @property
    def swap_disk(self) -> Dict[str, DynamicPage]:
        """Backward compatibility for Pager.swap_disk"""
        return self.l2_staging

    def render_context(self) -> str:
        # Sort by priority desc, then ID
        sorted_pages = sorted(
            self.l1_active.values(), 
            key=lambda p: (p.pinned, p.priority), 
            reverse=True
        )
        
        context_blocks = []
        for page in sorted_pages:
            display_id = page.id.replace("FILE:", "").replace("SYS:", "")
            header = f"=== {display_id} ==="
            context_blocks.append(f"{header}\n{page.content}\n")
        return "\n".join(context_blocks)
    
    def get_stats(self) -> Dict[str, int]:
        return {
            "l1_used": self.current_usage,
            "l1_capacity": self.capacity,
            "l1_count": len(self.l1_active),
            "l2_count": len(self.l2_staging),
            "l3_count": len(self.vector_store.documents) if self.vector_store else 0,
            # Backwards compatibility
            "pages_active": len(self.l1_active),
            "pages_swapped": len(self.l2_staging)
        }