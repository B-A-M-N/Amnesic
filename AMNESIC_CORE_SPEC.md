# The Amnesic Rules

Amnesic is a simple way to build agents that don't get confused. Most agents fail because they try to remember everything in one long chat history. Amnesic stops this by following four simple rules.

### 1. Explicit Context Management
The agent's focus is managed by choice, not by accident. Every file or data fragment in context is there because it was explicitly staged, and it can be removed just as explicitly. This prevents the "hoarding" of irrelevant data.

### 2. Take good notes (The Backpack)
Since the agent is going to "forget" the file it just read, it must save the important facts as **Artifacts**. Think of this like a backpack: the agent puts a sticky note in the backpack before it moves to the next task.

### 3. Wipe the slate clean
As soon as a fact is saved to the backpack, the agent's screen is wiped. It "forgets" the raw text it just read. If it didn't write it down in the backpack, it’s gone. This prevents old data from cluttering its brain.

### 4. Verify before acting
Every move the agent makes is checked by a **Validator**. The validator doesn't care about the agent's "thoughts"—it only checks if the move is safe and follows the rules.

---

## The Core Laws

*   **Active Context is evidence, volatile and untrusted.**
*   **Artifacts are law; only extracted state persists.**
*   **Reasoning is provisional; only the Backpack is truth.**
*   **No action without validation.**
*   **No recovery without rollback.**

---

## Architecture vs. Orchestration

Amnesic is not an orchestrator. Orchestrators route tasks; **Amnesic constrains cognition.** 

In a standard system, the agent is "free" to remember. In Amnesic, the agent is physically prevented from remembering *at all* unless it externalizes its state. This categorical difference transforms the agent from a conversational partner into a deterministic state machine.

---

## Authoritative State vs. Heuristic Search

To maintain truth, the system draws a hard line between two types of data:

1.  **Artifacts (Authoritative State):** These are the only things the agent "knows." They are symbolic, structured, and treated as ground truth.
2.  **Vectors (Heuristic Search):** These are just maps to help the agent find which file to look at. They are never used as a source of truth for reasoning.

---

### Why this works:
Traditional agents get "chatty" and drift off track because their history gets too long. Amnesic agents stay sharp because they only see:
1. The **Mission** (What to do).
2. The **Backpack** (What we already know).
3. The **Current File** (The only thing we are looking at right now).

**That's it. No history, no clutter, no confusion.**