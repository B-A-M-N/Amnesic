# Amnesic Protocol: Failure Taxonomy

This document formalizes the structural failure modes of standard "Implicit Memory" (Sliding Window/ReAct) architectures. The Amnesic Protocol is designed to be physically immune to these modes.

## 1. Context Thrash Loop (The Ouroboros)
*   **Definition:** A failure where the required context (Files A + B + Noise) exceeds the physical token limit.
*   **Mechanism:** Reading File B evicts File A. To process File B, the agent realizes it needs data from File A. It re-reads File A, which evicts File B.
*   **Amnesic Defense:** **Read-Then-Release**. Facts are committed to persistent Artifacts (Backpack) and L1 is flushed before the next file is staged.

## 2. Sliding Window Forgetting (The Drift)
*   **Definition:** Crucial instructions or early-acquired facts "slide" out of the context window as history grows.
*   **Mechanism:** As the agent performs turns, the System Prompt or initial observations are truncated. The agent loses the mission objective or forgets previously verified constraints.
*   **Amnesic Defense:** **Invariant Pinning**. The Mission and "Backpack" are present in every single turn, regardless of history length.

## 3. Implicit Memory Poisoning (The Hallucination Sink)
*   **Definition:** Incorrect reasoning or failed tool outputs remain in the chat history and are treated as "truth" in subsequent turns.
*   **Mechanism:** An agent makes a mistake in Turn 3. That mistake is now part of the context for Turn 4. The agent builds upon the error.
*   **Amnesic Defense:** **Auditor Rejection**. The Auditor prevents "Dirty State" from being saved as an Artifact. Only verified logic enters the persistent state.

## 4. Unbounded State Explosion (The Bloat)
*   **Definition:** The agent's performance degrades as the context window fills with redundant history.
*   **Mechanism:** Reasoning quality drops (needle-in-a-haystack) as the "Signal-to-Noise" ratio decreases within the window.
*   **Amnesic Defense:** **History Compression**. Turn history is summarized/collapsed, and L1 is kept near-empty (High Signal).

## 6. Conflict Paralysis (The Split Truth)
*   **Definition:** The agent encounters two contradictory facts (e.g., Version=1 in File A, Version=2 in File B) and has no formal mechanism to resolve the collision.
*   **Mechanism:** Standard agents usually adopt "Recency Bias," accepting the last thing they read, or they hallucinate a reconciliation.
*   **Amnesic Defense:** **Collision Detection**. The Auditor identifies when a `save_artifact` call conflicts with an existing invariant, forcing the agent to use a `Comparator` move to resolve the source of truth.

## 7. Incoherent Collaboration (The State Split)
*   **Definition:** Multiple agents or sessions working on the same task operate on stale or divergent information because they lack a shared, synchronized state.
*   **Mechanism:** Agent A fixes a bug. Agent B, unaware of the fix, writes new code that re-introduces the bug or breaks the fix.
*   **Amnesic Defense:** **Synchronized Sidecar (L3)**. All agents share a single L3 store. Any change by Agent A is immediately visible to Agent B in its next "Turn 0" context pull, ensuring global coherence without history bloat.
