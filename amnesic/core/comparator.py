from typing import Tuple, Dict
from .dynamic_pager import DynamicPager, DynamicPage

class Comparator:
    """
    A specialized controller for Dual-Slot Context operations.
    Allows temporary violation of the One-File rule for Diff/Merge tasks only.
    Enforces immediate 'Double-Eviction' after the operation.
    """
    def __init__(self, pager: DynamicPager):
        self.pager = pager

    def load_pair(self, file_a: str, content_a: str, file_b: str, content_b: str) -> bool:
        """
        Loads two files into L1 simultaneously.
        Returns True if successful, False if OOM.
        """
        # Calculate combined cost
        tokens_a = len(content_a) // 4
        tokens_b = len(content_b) // 4
        total_cost = tokens_a + tokens_b
        
        # Check if we can fit both
        # Note: We cheat the pager logic slightly by manually injecting
        if total_cost > self.pager.capacity:
            return False
            
        # Nuke current context to make room
        active = list(self.pager.active_pages.keys())
        for p in active:
            if "SYS:" not in p: # Keep system prompts
                self.pager.evict_to_l2(p)
        
        # Load Pair
        self.pager.active_pages[f"FILE:{file_a}"] = DynamicPage(
            id=f"FILE:{file_a}", content=content_a, tokens=tokens_a, last_accessed=self.pager.current_turn, priority=10
        )
        self.pager.active_pages[f"FILE:{file_b}"] = DynamicPage(
            id=f"FILE:{file_b}", content=content_b, tokens=tokens_b, last_accessed=self.pager.current_turn, priority=10
        )
        return True

    def purge_pair(self):
        """Strict enforcement: Evict all FILE pages immediately."""
        active = list(self.pager.active_pages.keys())
        for p in active:
            if "FILE:" in p:
                self.pager.evict_to_l2(p)
