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

## 5. Model Tuning & Context Partitioning

### The "Staging Normalizer" Pattern
Amnesic acts as a **Context Staging Normalizer**. By virtualizing infinite context into discrete, manageable pages, it allows smaller models (e.g., 8B parameters with 8k context) to achieve the functional performance of much larger models on long-horizon tasks.

*   **Scaling Small Models:** A 7B model with a 4k window can process a 100k-token repository by treating it as a stream of 2k chunks. The "Brain" never sees more than it can handle, but the "Backpack" retains the accumulated insight.
*   **Architecture Parity:** By enforcing the same amnesic rules on an 8B model and a 70B model, we normalize their output structure. This allows smaller models to serve as high-speed "Scouts" for larger implementing models.

### 5-Way Context Partitioning Strategy
For the protocol to remain invariant, the total context window of the LLM MUST be explicitly divided into functional zones. These zones are not fixed; they are **individually tunable parameters** that must be adjusted based on the specific model's architecture and the complexity of the mission.

| Zone | Purpose | Implementation Parameter |
| :--- | :--- | :--- |
| **1. System Prompt** | The "Rules of the Game." Invariants. | `context_floors["overhead"]` |
| **2. State Message** | The Backpack + Checklist. | `context_floors["overhead"]` |
| **3. Decision History** | Compressed action log. | `context_floors["overhead"]` |
| **4. Reasoning Room** | Space for Chain-of-Thought (CoT). | `context_floors["reasoning"]` |
| **5. Response Space** | Space for the tool call (JSON). | `context_floors["output"]` |
| **6. Active Context (L1)** | User data / Source code. | **Dynamic Remainder** |

### Dynamic Recalculation & Tuning
Amnesic dynamically calculates the **L1 Capacity** (the remainder) at every turn to ensure the guaranteed floors are never violated:
`L1_Capacity = Total_Window - (Overhead_Floor + Reasoning_Floor + Output_Floor)`

**Individually Tunable Realities:**
*   **Reasoning-Heavy Models:** If using a model that requires extensive Chain-of-Thought to remain accurate (e.g., Llama 3 8B), increase `reasoning` to 8192+.
*   **High-Throughput Missions:** For simple data extraction, decrease `reasoning` and `overhead` to maximize the `L1_Capacity` for reading large files.
*   **Small Window Scaling (Theoretical):** For models with very small windows (e.g., 4k), you *can* shrink floors to the absolute minimum to allow a 1k L1 "peep-hole." However, this is practically limited by the **Peep-Hole Effect**: if the window is too small to fit a coherent semantic unit (like a single function), the agent will thrash. Realistically, this requires highly specialized "micro-chunking" strategies.

**Example: Advanced Tuning**
```python
session = AmnesicSession(
    max_total_context=32768,
    context_floors={
        "reasoning": 16384, # Give the model massive room to plan
        "output": 4096,     # Ensure complex code writes aren't truncated
        "overhead": 4096    # Room for deep history and complex rules
    }
)
# Result: L1_Capacity is locked to ~8k tokens. 
# The agent will process data in 8k chunks, but with maximum "Cognitive Oxygen."
```

**CRITICAL:** Tunability is the key to scaling. By adjusting these limits, you can normalize context staging across a heterogeneous fleet of LLMs, ensuring a 7B model and a 70B model operate with the same structural integrity.

**CRITICAL:** If `L1_Capacity` is too high, the LLM will truncate the System Prompt or History, causing it to "forget" the mission rules or get stuck in loops. Correct tuning ensures the "Cognitive Oxygen" (Reasoning Room) is never crowded out by "Data Noise" (Active Context).