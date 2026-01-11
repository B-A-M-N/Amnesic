from typing import List

def compress_history(history: List[str], max_turns: int = 5) -> str:
    """
    Prevents the 'Ledger Explosion' by collapsing old turns.
    """
    if len(history) <= max_turns:
        return "\n".join(history)

    # Everything before the last 3 turns gets collapsed
    # We keep the last 3 for immediate context
    cutoff = 3
    if len(history) <= cutoff:
        return "\n".join(history)
        
    old_history = history[:-cutoff]
    recent_history = history[-cutoff:]

    # We summarize the old history into a single 'Milestone'
    summary = f"MILESTONE: Successfully processed {len(old_history)} initial steps."
    
    return f"{summary}\n" + "\n".join(recent_history)