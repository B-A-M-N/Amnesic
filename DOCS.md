# Amnesic Protocol: Technical Documentation

## 1. Architectural Components

### The Manager (The Brain)
The Manager is the LLM context. It receives the current state (Backpack + L1 RAM View) and decides the next **ManagerMove**.
*   **Input:** System Prompt (Rules) + User Prompt (State) + History.
*   **Output:** Structured JSON command (e.g., `{"tool_call": "stage_context", "target": "main.py"}`).

### The Auditor (The Policy Engine)
The Auditor intercepts every ManagerMove *before* execution.
*   **Deterministic Checks:**
    *   **Syntax:** Is the tool call valid?
    *   **Infrastructure:** Does the file exist? Is L1 full?
    *   **Hygiene:** Are we overwriting an existing artifact? (Stagnation check).
    *   **Safety:** Are we accessing a forbidden path?
*   **Semantic Checks (Vector/LLM):**
    *   **Relevance:** Does this action help the mission? (Vector similarity).
    *   **Grounding:** Is the artifact we are saving actually present in the current text? (Prevents hallucinations).

### The Pager (Dynamic Memory)
Manages the "Physical" limits of the context window.
*   **L1 (Active RAM):** The actual context sent to the LLM. Limited by `l1_capacity`.
*   **L2 (Swap):** When L1 is full, pages are evicted here. They are not visible to the LLM but can be re-staged instantly.
*   **Substrate:** The physical disk.

### The Sidecar (The Backpack)
A persistent, structured knowledge graph shared across sessions.
*   **Artifacts:** Named, immutable facts (e.g., `API_KEY`, `USER_SCHEMA`).
*   **Vector Store:** Allows fuzzy retrieval of artifacts.

---

## 2. Failure Taxonomy & Handling

Amnesic is designed to detect and recover from specific agent failure modes.

| Failure Mode | Description | Amnesic Solution |
| :--- | :--- | :--- |
| **Context Drift** | Agent forgets early instructions as context fills. | **Strict Amnesia:** Wipe context after every file. |
| **Hallucination** | Agent invents data not in the file. | **Grounding Check:** Auditor rejects artifacts not found in L1. |
| **Looping (Stagnation)** | Agent tries the same action repeatedly. | **Stagnation Breaker:** Auditor detects duplicate moves and forces a strategy shift. |
| **Dependency Hell** | Agent guesses at missing imports. | **Ignorance Detection:** Agent must verify imports exist (`proof_ignorance.py`). |
| **Infinite Horizon** | Task requires reading more tokens than exist. | **Stream Processing:** Read A -> Save -> Wipe -> Read B (`proof_native_overflow.py`). |

---

## 3. Configuration Reference

### `AmnesicSession` Parameters

*   `mission` (str): The prompt/goal.
*   `root_dir` (str): Allowed working directory (sandbox).
*   `model` (str): LLM model name (e.g., "rnj-1:latest").
*   `l1_capacity` (int): Max tokens for Active Context (default: 32768).
*   `elastic_mode` (bool):
    *   `False` (Default): Strict One-File Limit. Staging B evicts A.
    *   `True`: Allow multiple files until `l1_capacity` is hit.
*   `audit_profile` (str): "STRICT_AUDIT", "FLUID_READ", or "HIGH_SPEED".
*   `strategy` (str): Initial persona prompt injection.

---

## 4. Advanced Concepts

### Comparator (Dual-Slot Logic)
Used for diffing files.
1.  Loads File A and File B into reserved slots in L1.
2.  Locks the context (no new files allowed).
3.  Agent performs comparison.
4.  **Double Eviction:** Both files are purged immediately after to prevent state pollution.

### Prefetching
If the agent is reading `main.py` and sees `import utils`, the system can proactively load `utils.py` into **L2 Cache**. When the agent requests `utils.py`, it loads instantly without disk I/O.

### Determinism
By fixing the random seed and enforcing strict state transitions, Amnesic can achieve 100% replayability for debugging complex agent logic. See `proof_determinism.py`.

---

## 5. Model Tuning & Context Normalization

### The "Staging Normalizer" Pattern
Amnesic acts as a **Context Staging Normalizer**. By virtualizing infinite context into discrete, manageable pages, it allows smaller models (e.g., 8B parameters with 8k context) to achieve the functional performance of much larger models on long-horizon tasks.

*   **Scaling Small Models:** A 7B model with a 4k window can process a 100k-token repository by treating it as a stream of 2k chunks. The "Brain" never sees more than it can handle, but the "Backpack" retains the accumulated insight.
*   **Multi-Model Pipelines:** In pipelines where agents hand off tasks, Amnesic normalizes the state. A "Scout" agent (8B) can distill a massive dataset into a dense 1k-token artifact, which is then handed to a "Coder" agent (70B) for high-precision synthesis.

### Tuning `l1_capacity`
**CRITICAL:** For Amnesic to work, you MUST tune `l1_capacity` to the specific constraints of your LLM.

*   **Total Window** = The model's hard limit (e.g., 8192 tokens).
*   **System Overhead** = Prompts + History (~1000-2000 tokens).
*   **Output Reserve** = Space needed for the model's response (~1000 tokens).
*   **L1 Capacity** = Total Window - (Overhead + Output Reserve).

**Example Configuration:**
```python
# For a model with 8k context
session = AmnesicSession(
    ...,
    max_total_context=8192,
    context_floors={
        "reasoning": 1024,  # Reserve for thinking
        "output": 1024,     # Reserve for response
        "overhead": 2048    # Reserve for system prompts/history
    }
)
# Resulting L1 Capacity = ~4096 tokens
```
If `l1_capacity` is set too high, the model will truncate the system prompt or history, breaking the invariant enforcement. If set too low, the agent will "thrash," constantly staging and unstaging files to read simple functions.
