from typing import List

def compress_history(history: List[str], max_turns: int = 5) -> str:
    """
    Prevents the 'Ledger Explosion' by collapsing old turns.
    """
    if len(history) <= max_turns:
        return "\n".join(history)

    # Everything before the last 10 turns gets collapsed
    # We keep the last 10 for immediate context
    cutoff = 10
    if len(history) <= cutoff:
        return "\n".join(history)
        
    old_history = history[:-cutoff]
    recent_history = history[-cutoff:]

    # Summarize the old history with outcome counts
    successes = len([h for h in old_history if "-> PASS" in h or "-> HALT" in h])
    rejections = len([h for h in old_history if "-> REJECT" in h])
    
    summary = f"MILESTONE: Successfully processed {len(old_history)} initial steps ({successes} successful, {rejections} rejected)."
    
    return f"{summary}\n" + "\n".join(recent_history)