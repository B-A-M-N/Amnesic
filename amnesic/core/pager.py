import logging
from typing import List, Dict, Optional, TypedDict
from pydantic import BaseModel

logger = logging.getLogger("amnesic.pager")

# --- Types ---
class MemoryPage(BaseModel):
    id: str                 # e.g., "file:auth.py" or "artifact:code_patch_1"
    content: str            # The actual text
    tokens: int             # Pre-calculated token count
    last_accessed: int      # Turn number (for LRU)
    pinned: bool = False    # If True, never evict (e.g., Mission Statement)

class PagingStats(TypedDict):
    l1_used: int
    l1_capacity: int
    pages_active: int
    pages_swapped: int

class Pager:
    def __init__(self, capacity_tokens: int = 3000):
        """
        The MMU (Memory Management Unit).
        capacity_tokens: The Safe Limit (Total Context - Output Reserve - System Prompt)
        """
        self.capacity = capacity_tokens
        self.active_pages: Dict[str, MemoryPage] = {} # L1 Cache
        self.swap_disk: Dict[str, MemoryPage] = {}    # L2 Storage (Python Dict for MVP)
        self.current_turn = 0

    def tick(self):
        """Call this at the start of every turn to update LRU clocks."""
        self.current_turn += 1

    def pin_page(self, page_id: str, content: str):
        """Creates a page that cannot be evicted (e.g. The Mission)."""
        self._load_page(page_id, content, pinned=True)

    def request_access(self, page_id: str, content: Optional[str] = None) -> bool:
        """
        The Manager requests a file.
        The Pager handles the 'How'.
        Returns True if successful, False if file creates OOM (Out of Memory) even after eviction.
        """
        # 1. Update Clock
        if page_id in self.active_pages:
            self.active_pages[page_id].last_accessed = self.current_turn
            return True

        # 2. Check Swap (L2)
        if page_id in self.swap_disk:
            page = self.swap_disk.pop(page_id)
            page.last_accessed = self.current_turn
            # If new content provided (e.g. reload from disk), update it
            if content:
                page.content = content
                page.tokens = len(content) // 4
            content = page.content 
            pinned = page.pinned
        elif content is None:
             # Cannot load what we don't have
             logger.error(f"PageFault: {page_id} not found in L1 or L2.")
             return False
        else:
            pinned = False
        
        # 3. Create Page Object (Calculates tokens)
        # Note: In production, use a real tokenizer. Here we approx 4 chars = 1 token.
        tokens = len(content) // 4 
        new_page = MemoryPage(
            id=page_id, 
            content=content, 
            tokens=tokens, 
            last_accessed=self.current_turn,
            pinned=pinned
        )

        # 4. Check Budget & Evict
        if not self._make_space(new_page.tokens):
            logger.warning(f"OOM: Cannot load {page_id} ({tokens} toks). Page too large for L1.")
            return False

        # 5. Load
        self.active_pages[page_id] = new_page
        return True
        
    def _load_page(self, page_id: str, content: str, pinned: bool):
        """Internal load helper."""
        tokens = len(content) // 4
        new_page = MemoryPage(
            id=page_id,
            content=content,
            tokens=tokens,
            last_accessed=self.current_turn,
            pinned=pinned
        )
        if self._make_space(new_page.tokens):
            self.active_pages[page_id] = new_page

    def evict(self, page_id: str):
        """Explicitly moves a page from L1 to L2."""
        if page_id in self.active_pages:
            page = self.active_pages.pop(page_id)
            self.swap_disk[page_id] = page
            logger.info(f"Evicted {page_id} to Swap. Freed {page.tokens} tokens.")

    def _make_space(self, required_tokens: int) -> bool:
        """The Eviction Algorithm (LRU)."""
        while self.current_usage + required_tokens > self.capacity:
            # Find candidate: Unpinned, oldest access
            candidates = [p for p in self.active_pages.values() if not p.pinned]
            
            if not candidates:
                return False # Cannot evict anything else (Everything is pinned)
            
            # Sort by last_accessed (Smallest = Oldest)
            victim = min(candidates, key=lambda p: p.last_accessed)
            
            # Swap out
            self.evict(victim.id)
            
        return True

    @property
    def current_usage(self) -> int:
        return sum(p.tokens for p in self.active_pages.values())

    def render_context(self) -> str:
        """Constructs the actual string to feed the LLM."""
        # Sort by relevance or type if needed. For now, simple concat.
        context_blocks = []
        for page in self.active_pages.values():
            header = f"--- SOURCE: {page.id} ---"
            context_blocks.append(f"{header}\n{page.content}\n")
        return "\n".join(context_blocks)
    
    def get_stats(self) -> PagingStats:
        return {
            "l1_used": self.current_usage,
            "l1_capacity": self.capacity,
            "pages_active": len(self.active_pages),
            "pages_swapped": len(self.swap_disk)
        }