# Amnesic Protocol: Capabilities Verification Matrix

This document tracks the verification status of the advanced cognitive capabilities enabled by the Amnesic architecture.

**Core Thesis:** Amnesic replaces implicit conversational memory with queryable, externalized infrastructure.

## Phase 1: The Foundation (Completed)

| Capability | Definition | Verification Status | Proof File |
| :--- | :--- | :--- | :--- |
| **Dynamic Retrieval** | Ability to fetch files into Active Context on demand. | ✅ **VERIFIED** | `tests/proofs/basic_semantic_proof.py` |
| **Context Clearing** | Ability to clear Active Context to 0% usage while retaining state. | ✅ **VERIFIED** | `tests/proofs/basic_semantic_proof.py` |
| **Rule Persistence** | Ability to apply a "rule" found in File A to data in File B without keeping File A loaded. | ✅ **VERIFIED** | `tests/proofs/advanced_semantic_proof.py` |
| **Loop Prevention** | Ability to avoid the repetitive reading loops via explicit state tracking. | ✅ **VERIFIED** | `tests/control_proofs/control_basicsemantic_proof.py` |

---

## Phase 2: State Externalization (To Be Proven)

These capabilities represent the architectural benefits of the system.

### 1. Dependency Garbage Collection
*   **Claim:** The system can drop context/facts that are structurally invalidated (e.g., a function deletion in the AST invalidates the Artifact describing it).
*   **The Test:** "Garbage Collection Test."
    1. Agent maps `file_a.py`. Extracts `func_x`.
    2. *External Event:* `func_x` is deleted from `file_a.py`.
    3. Agent must identify `Artifact: func_x` as "Stale/Orphaned" via AST diffing, without reading the file text.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_gc.py`

### 2. State Snapshotting
*   **Claim:** The agent can revert its *conceptual understanding* (Artifact State) to a previous checkpoint to analyze regression.
*   **The Test:** "State Reversion Test."
    1. Agent solves a task. State is Checkpointed (T1).
    2. Agent is fed bad info, corrupting State (T2).
    3. Agent must revert to T1 to restore correct reasoning.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_time_travel.py`

### 3. Contract Enforcement
*   **Claim:** The system can enforce behavioral contracts (e.g., "Output must be JSON") by checking `ManagerMove` against a Schema Artifact before execution.
*   **The Test:** "Constraint Validation Test."
    1. Establish an "Invariant Artifact" (e.g., "NO_GLOBAL_VARS").
    2. Agent attempts to write code with a global var.
    3. Validator/Decision Engine rejects it based on the Artifact.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_contracts.py`

### 4. Heuristic Variable Matching
*   **Claim:** The agent can identify that Function A (new) serves the same purpose as Function B (old) via structural/semantic triangulation.
*   **The Test:** "Semantic Matching Test."
    1. Analyze `legacy.py`. Save Intent Artifacts.
    2. Analyze `refactored.py` (different names).
    3. Agent must map Legacy Artifacts to New Functions correctly.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/advanced_semantic_proof.py`

### 5. State Synchronization
*   **Claim:** Two distinct agents can operate on different slices of the codebase while sharing a single Semantic State (Artifacts/Vectors).
*   **The Test:** "State Transfer Test."
    1. Agent A maps the repo and terminates.
    2. Agent B wakes up, sees Agent A's Artifacts, and implements a feature without scanning the repo again.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_hive_mind.py`

### 6. Speculative Execution
*   **Claim:** Speculative branches can be tested and discarded without poisoning the main context.
*   **The Test:** "Speculative Branching Test."
    1. Fork State into Branch A and Branch B.
    2. Branch A fails.
    3. Main Agent discards Branch A, merges Branch B.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_isolation.py`

### 7. Cognitive Load Shaping
*   **Claim:** Restricting the agent's view to a specific dependency radius improves reasoning quality compared to full-context visibility.
*   **The Test:** "Signal-to-Noise Test."
    1. Task: Find a bug in 10 lines of code surrounded by 10,000 lines of noise.
    2. Compare Success Rate: Full Context vs. Targeted Amnesic Paging.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_cognitive_load.py`

### 8. Determinism
*   **Claim:** Given the same Artifact State and Active Context, the Agent's next move is deterministic.
*   **The Test:** "Determinism Test."
    1. Run a session. Log inputs/state.
    2. Re-run 100 times. Verify 0% drift in decision making.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_determinism.py`

### 9. Missing Data Detection
*   **Claim:** The agent can detect "Ignorance" (missing artifacts) and formulate specific queries to resolve it.
*   **The Test:** "Missing Data Test."
    1. Agent is given a task requiring data X (missing).
    2. Agent must issue a specific `halt_and_ask` or `search` for X, rather than hallucinating X.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_ignorance.py`

### 10. Elastic Context Management
*   **Claim:** The framework can switch from 'Strict Amnesia' to 'Elastic Context', allowing multiple documents in context and manual eviction control.
*   **The Test:** "Elastic Context Test."
    1. Enable `elastic_mode=True`.
    2. Agent loads File A.
    3. Agent loads File B without evicting File A.
    4. Agent performs an action while both are visible.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_elastic_context.py`

### 11. Semantic Self-Correction
*   **Claim:** The agent can identify and correct its own incorrect artifacts when presented with new evidence (Non-Monotonic Reasoning).
*   **The Test:** "Correction Test."
    1. Agent extracts wrong value from Source A.
    2. Agent reads Source B, which invalidates Source A.
    3. Agent updates/overwrites the existing artifact with correct data.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_self_correction.py`

### 12. Long-Horizon Execution
*   **Claim:** The framework enables sustained reasoning quality over extremely long horizons (50+ turns) by preventing context saturation.
*   **The Test:** "Long-Context Test."
    1. Deep dependency chain (10+ steps).
    2. Agent must maintain state through 40+ atomic context cycles.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_marathon.py`

### 13. Resource Efficiency
*   **Claim:** The framework enables high-complexity reasoning on models or budgets with extremely small context windows (e.g., 512 tokens).
*   **The Test:** "Low-Resource Test."
    1. Multi-file retrieval task.
    2. L1 Capacity set to 512 tokens.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_extreme_efficiency.py`

### 14. Multi-Root Workspace Support
*   **Claim:** The framework enables a single agent to operate securely across multiple distinct repository roots, allowing cross-repo bug discovery and fixing.
*   **The Test:** "Multi-Root Test."
    1. Mount Repo A (Library) and Repo B (Application).
    2. Agent extracts API contract from Repo A.
    3. Agent fixes calling code in Repo B based on Repo A's truth.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_workspace_nexus.py`

### 15. Cross-Model Invariance
*   **Claim:** The protocol ensures equivalent artifact production across materially different model architectures (e.g., 8B vs 24B).
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_model_invariance.py`

### 16. Explicit Failure Taxonomy
*   **Claim:** The system classifies and surfaces specific failure modes (Deadlock, Starvation, Thrash) rather than failing cryptically.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_failure_taxonomy.py`

### 17. Human-in-the-Loop Resilience
*   **Claim:** The Auditor catches and contains damage from human-injected errors (e.g., manual artifact corruption) during a session.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/proofs/proof_human_friction.py`

---

## Phase 3: Systemic Hardening (Security)

These capabilities ensure the framework is safe for production use by enforcing physical constraints.

### 15. Path Isolation
*   **Claim:** The agent is physically prevented from accessing any file outside the designated root directories.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/unit_tests/test_hardening_unit.py`

### 16. Pre-execution Safety Checks
*   **Claim:** Security violations are caught in the system logic before reaching the LLM, preventing prompt-injection attempts.
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `tests/unit_tests/test_hardening_unit.py`

### 17. Output Size Limiting
*   **Claim:** The system rejects generated payloads that exceed safe size limits (1MB), protecting against "hallucination bloat."
*   **Status:** ✅ **VERIFIED**
*   **Proof:** `amnesic/decision/worker.py` (via Pydantic Validators)