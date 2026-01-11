# Amnesic Framework: Capabilities Verification Matrix

This document tracks the verification status of the advanced cognitive capabilities enabled by the Amnesic architecture. 

**Core Thesis:** Amnesic is not just context dumping; it is **Externalized Cognition**, where memory is replaced by queryable infrastructure.

## Phase 1: The Foundation (Completed)

| Capability | Definition | Verification Status | Proof File |
| :--- | :--- | :--- | :--- |
| **Dynamic Retrieval** | Ability to fetch files into L1 on demand. | ✅ **VERIFIED** | `tests/proofs/basic_semantic_proof.py` |
| **Forced Amnesia** | Ability to clear L1 to 0% usage while retaining state. | ✅ **VERIFIED** | `tests/proofs/basic_semantic_proof.py` |
| **Logic Persistence** | Ability to apply a "rule" found in File A to data in File B without keeping File A loaded. | ✅ **VERIFIED** | `tests/proofs/advanced_semantic_proof.py` |
| **Loop Resistance** | Ability to avoid the repetitive reading loops seen in standard ReAct agents via explicit state. | ✅ **VERIFIED** | `tests/control_proofs/control_basicsemantic_proof.py` |

---

## Phase 2: Externalized Cognition (To Be Proven)

These capabilities represent the "fallout" of the architecture. They are theoretically sound but require specific executable proofs to be considered "Features."

### 1. Context Garbage Collection (Structural GC)
*   **Claim:** The system can drop context/facts that are structurally invalidated (e.g., a function deletion in the AST invalidates the Artifact describing it).
*   **The Test:** "The Dead Node Proof."
    1. Agent maps `file_a.py`. Extracts `func_x`.
    2. *External Event:* `func_x` is deleted from `file_a.py`.
    3. Agent must identify `Artifact: func_x` as "Stale/Orphaned" via AST diffing, without reading the file text.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_gc.py`

### 2. Time-Traveling Context
*   **Claim:** The agent can revert its *conceptual understanding* (Artifact State) to a previous checkpoint to analyze regression.
*   **The Test:** "The Regression Proof."
    1. Agent solves a task. State is Checkpointed (T1).
    2. Agent is fed bad info, corrupting State (T2).
    3. Agent must revert to T1 to restore correct reasoning.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_time_travel.py`

### 3. Contract Enforcement
*   **Claim:** The system can enforce behavioral contracts (e.g., "Output must be JSON") by checking `ManagerMove` against a Schema Artifact before execution.
*   **The Test:** "The Guardrail Proof."
    1. Establish an "Invariant Artifact" (e.g., "NO_GLOBAL_VARS").
    2. Agent attempts to write code with a global var.
    3. Auditor/Manager rejects it based on the Artifact, not the Prompt.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_contracts.py`

### 4. Intent Recovery
*   **Claim:** The agent can identify that Function A (new) serves the same purpose as Function B (old) via structural/semantic triangulation.
*   **The Test:** "The Refactor Match Proof."
    1. Analyze `legacy.py`. Save Intent Artifacts.
    2. Analyze `refactored.py` (different names).
    3. Agent must map Legacy Artifacts to New Functions correctly.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/advanced_semantic_proof.py`

### 5. Multi-Agent Reality Sync
*   **Claim:** Two distinct agents can operate on different slices of the codebase while sharing a single Semantic State (Artifacts/Vectors).
*   **The Test:** "The Relay Proof."
    1. Agent A (Scout) maps the repo and dies.
    2. Agent B (Coder) wakes up, sees Agent A's Artifacts, and implements a feature without scanning the repo again.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_hive_mind.py`

### 6. Failure-Mode Isolation
*   **Claim:** Speculative branches can be tested and discarded without poisoning the main context.
*   **The Test:** "The Branching Proof."
    1. Fork State into Branch A and Branch B.
    2. Branch A hallucinates/fails.
    3. Main Agent discards Branch A, merges Branch B.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_isolation.py`

### 7. Cognitive Load Shaping
*   **Claim:** Restricting the agent's view to a specific dependency radius improves reasoning quality compared to full-context visibility.
*   **The Test:** "The Noise Proof."
    1. Task: Find a bug in 10 lines of code surrounded by 10,000 lines of noise.
    2. Compare Success Rate: Full Context vs. Targeted Amnesic Paging.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_cognitive_load.py`

### 8. Determinism Levers
*   **Claim:** Given the same Artifact State and L1 Context, the Agent's next move is deterministic.
*   **The Test:** "The Replay Proof."
    1. Run a session. Log inputs/state.
    2. Re-run 100 times. Verify 0% drift in decision making.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_determinism.py`

### 9. Introspective Questioning
*   **Claim:** The agent can detect "Ignorance" (missing artifacts) and formulate specific queries to resolve it.
*   **The Test:** "The Known-Unknowns Proof."
    1. Agent is given a task requiring data X (missing).
    2. Agent must issue a specific `halt_and_ask` or `search` for X, rather than hallucinating X.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_ignorance.py`

### 10. Elastic Context Management
*   **Claim:** The framework can switch from 'Strict Amnesia' to 'Elastic Context', allowing multiple documents in L1 and manual eviction control.
*   **The Test:** "The Multi-File L1 Proof."
    1. Enable `elastic_mode=True`.
    2. Agent loads File A.
    3. Agent loads File B without evicting File A.
    4. Agent performs an action while both are visible.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_elastic_context.py`

### 11. Semantic Self-Correction
*   **Claim:** The agent can identify and correct its own incorrect artifacts when presented with new evidence (Non-Monotonic Reasoning).
*   **The Test:** "The Oops Proof."
    1. Agent extracts wrong value from Source A.
    2. Agent reads Source B, which invalidates Source A.
    3. Agent updates/overwrites the existing artifact with correct data.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_self_correction.py`

### 12. The Marathon Session
*   **Claim:** The framework enables sustained reasoning quality over extremely long horizons (50+ turns) by preventing context saturation.
*   **The Test:** "The Infinite Horizon Proof."
    1. Deep dependency chain (10+ steps).
    2. Agent must maintain state through 40+ atomic context cycles.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_marathon.py`

### 13. Resource Efficiency (Micro-Kernel)
*   **Claim:** The framework enables high-complexity reasoning on models or budgets with extremely small context windows (e.g., 512 tokens).
*   **The Test:** "The Sub-Small Proof."
    1. Multi-file retrieval task.
    2. L1 Capacity set to 512 tokens.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_extreme_efficiency.py`
