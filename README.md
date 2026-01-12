# Amnesic: Context Offloading Protocol

**Amnesic** is a context-management framework for LLM agents that enables reliable long-horizon reasoning and code modification by enforcing strict context staging and persistent semantic state extraction.

Amnesic enables agents to operate over unbounded information while maintaining a strictly bounded context window. It achieves this by treating the context window as a volatile staging area and persistently storing only extracted semantic and structural state in an external "State Store."

## Core Philosophy

Standard agents suffer from **Context Drift**: as the conversation grows, reasoning degrades, costs increase, and earlier instructions are lost in the noise.

**Amnesic** mitigates semantic drift by forcing all long-term knowledge into explicit, inspectable state transitions instead of implicit conversational history.

Amnesic manages context using a hierarchical memory model:
*   **Active Context (L1):** Expensive, extremely limited, volatile. Only holds the *immediate* file or data fragment being analyzed.
*   **Persisted State (L2/L3):** Cheap, persistent, unlimited. Holds the *extracted insights*, contracts, and decisions (Artifacts & Vectors).

## System Architecture

The framework is implemented as a **LangGraph** deterministic state machine, ensuring persistent state across turns via a checkpointing system.

*   **The Mapper:** Performs real-time Structural AST scans and Vector Indexing to provide the agent with a structural view of the environment.
*   **The Decision Engine:** Decides moves based on the Active Context and Shared Ground Truth (Artifacts).
*   **The Context Pager:** Enforces the **Strict Token Limit** (e.g., 1500 tokens). Manages context loading, auto-eviction, and **Context Prefetching** for background staging.
*   **The Adaptive Driver (Healing):** Implements **JSON Repair**, **Key-Value Fallback**, and **Typo Healing** to ensure stable reasoning even when smaller models (e.g., 8b) produce semi-structured or malformed outputs.
*   **The Comparator:** A specialized controller for `diff` and `merge` tasks. Temporarily allows two files in context while enforcing a strict cleanup policy.
*   **The Policy Validator:** Intercepts and validates every move against semantic contracts and structural invariants.

---

## Specialized Workflows (Presets)

Amnesic includes specialized presets for high-stakes enterprise tasks:

### 1. Data Sanitization
Ensures that an agent can ingest highly sensitive proprietary data (Active Context), extract the sanitized logic or public interface (Artifact), and permanently discard the sensitive context.
*   *Verification:* `tests/proofs/proof_clean_room.py`

### 2. Legacy Migration
Migrates legacy code (e.g., unstructured patterns) into clean, modern architectures by strictly following a "Schema Artifact" while architecturally forbidden from preserving legacy naming or global state.
*   *Verification:* `tests/proofs/proof_rosetta.py`

---

## Proven Capabilities

The following capabilities are verified in the regression suite. Detailed traces are available in [PROVEN_LOGS.md](PROVEN_LOGS.md).

### 1. Semantic Intelligence & Retrieval
*   **Cross-File Retrieval:** Success in retrieving $X$ from File A and $Y$ from File B, then summing them, while architecturally forbidden from holding both in memory.
*   **Symbolic Math & Legacy Support:** The kernel supports deterministic arithmetic (`+`, `-`, `*`, `/`) and legacy keyword processing via a specialized calculation engine, preventing LLM arithmetic hallucination.
*   **Dynamic Logic Analysis:** Agent enters a system with 0 knowledge, discovers a hidden math rule in a logic file, and applies it to hidden data.
*   **Heuristic Variable Matching:** Successfully extracts data from variables with misleading names by prioritizing structural intent over string similarity.

### 2. Adaptive Reasoning (Driver Healing)
*   **Key-Value Fallback:** Successfully extracts intent from smaller models that revert to "KEY: Value" text output instead of raw JSON.
*   **Typo Healing:** Automatically corrects common schema typos (e.g., `rationate` -> `rationale`) to prevent Pydantic validation crashes.
*   **Aggressive JSON Extraction:** Strips `<think>` tags, markdown fences, and conversational fluff to isolate the structured core of the response.

### 3. Code Engineering
*   **Single-File Patch:** Identifies and applies fixes to hardcoded bugs in a single turn.
*   **Multi-File Refactoring:** Performs multi-file architectural refactoring (e.g., updating an API signature and propagating the change to all call sites) without holding both files in context.

### 4. Memory Infrastructure
*   **Dependency Garbage Collection:** Proactively detects when a file becomes semantically unreachable after a refactor and removes it to save cognitive load.
*   **LRU Eviction:** The Pager automatically purges the Least Recently Used (LRU) context when the token budget is exceeded.
*   **Context Prefetching:** Allows the Decision Engine to stage the *next* predicted file into memory (L2) while the Agent is still processing the current file, reducing latency.
*   **Diff/Merge Comparison:** Enables semantic `diff` operations by safely holding two versions of a file in context, with a guaranteed wipe once the comparison artifact is generated.
*   **State Snapshotting:** Snapshots the agent's "understanding" at a specific point in time. Agent can correctly explain a past bug even after the code on disk has been fixed.
*   **State Synchronization:** Two distinct agent instances sharing a single State Store. Agent B knows what Agent A learned without performing any File I/O.

### 5. Governance & Reliability
*   **Contract Enforcement:** Validates implementation code against a "Contract Artifact" (spec) and halts on violations (e.g., wrong return type).
*   **Speculative Execution:** Speculative changes are quarantined in a hypothesis layer; destructive failures do not poison the main codebase.
*   **Missing Dependency Detection:** Identifies missing dependencies (e.g., an import to a non-existent file) and explicitly halts to ask for context instead of hallucinating.

### 6. Security & Hardening
*   **Path Isolation:** Enforces strict chroot-like isolation. Agent is architecturally forbidden from accessing files outside the approved `root_dirs`.
*   **Pre-execution Safety Checks:** Intercepts security violations (traversal, sensitive files) in the session logic *before* calling the LLM, preventing prompt-injection attacks.
*   **Output Size Limiting:** Validates and caps generated content size (1MB) to prevent system memory saturation from massive hallucinations.
*   **Strict Context Limits:** Strictly enforces the capacity at the driver level, ensuring the model cannot process beyond the defined window.

### 7. Agent Dynamics & Strategy
*   **Multi-Phase Strategy:** The agent dynamically switches strategies mid-session. It starts as an **Architect** to plan a complex refactor and then transforms into an **Implementer** to execute it surgically.
*   **Loop Prevention:** Outperforms standard ReAct agents which loop or fail under the same context window constraints.

## Adaptive Context Management

Amnesic allows users and agents to dynamically tune the context strategy based on the task complexity.

### 1. Strict Amnesia (Default)
In this mode, the agent is restricted to a **One-File-In-L1** policy. This is ideal for maximizing reasoning density and preventing distraction in large codebases.
*   **Protocol:** `stage_context` -> `save_artifact` -> `unstage_context` (Automated or Manual).
*   **Benefit:** Zero context drift; 100% focus on the current atomic unit of work.

### 2. Elastic Mode (Advanced)
For tasks requiring cross-document reasoning (e.g., comparing a library signature with its implementation), Amnesic can be switched to **Elastic Mode**.
*   **Enabling:** Set `elastic_mode=True` in the `AmnesicSession`.
*   **Capability:** Allows multiple files to coexist in L1 simultaneously until the token budget is reached.
*   **Manual Control:** The agent gains the ability to choose *exactly* when to offload context using `unstage_context(path)`.

```python
# Advanced Workflow: Multi-File Cross-Referencing
session = AmnesicSession(
    mission="Compare the API spec with the service implementation.",
    root_dir="./src",
    elastic_mode=True,
    l1_capacity=4000
)
```

### 3. Manual Offloading & Purging
Even in Strict mode, advanced workflows can utilize manual purging to "re-roll" reasoning or clear L1 for high-priority emergency tasks:
*   **`unstage_context(path)`**: Explicitly evicts a file.
*   **`save_artifact` (Bridge)**: Offloads the *essence* of the file into L2 before purging the raw text from L1.

## Eviction Thresholds & Policy Tuning

Amnesic provides two main levers for controlling *when* context is purged:

### 1. Token Thresholds (LRU)
The `DynamicPager` uses an **Eviction Score** to decide which files to purge when the `l1_capacity` is exceeded.
*   **Recency:** How many turns ago the file was accessed.
*   **Priority:** Fixed importance (Mission=10, User File=8, Artifact=5).
*   **Tuning:** You can adjust the `l1_capacity` to force more frequent or less frequent purges. A smaller window (e.g., 1000 tokens) forces the agent to extract state more aggressively.

### 2. Event-Driven Purging (Strict Mode)
In **Strict Amnesia** mode, purging is tied to the **Semantic Extraction Event**:
*   **Trigger:** Calling `save_artifact` automatically triggers a purge of all non-pinned files in L1.
*   **Why:** This ensures that once a "fact" is safely in L2 (Backpack), the "noise" (File Text) is immediately discarded to prevent hallucination.

### 3. Custom Kernel Policies
You can inject deterministic `KernelPolicies` to force purges based on complex state conditions:

```python
# Force-purge context if a 'CRITICAL_VULNERABILITY' artifact is found
vulnerability_policy = KernelPolicy(
    name="PurgeOnThreat",
    condition=lambda state: any("VULNERABILITY" in a.identifier for a in state.artifacts),
    reaction=lambda state: ManagerMove(
        thought_process="Critical threat found. Purging L1 for safety.",
        tool_call="unstage_context",
        target="ALL"
    )
)

session = AmnesicSession(..., policies=[vulnerability_policy])
```

---

## Usage Guide

### Prerequisites
*   **Python 3.10+**
*   **Ollama** running locally (defaults to `rnj-1:8b-cloud`).

### Installation
```bash
pip install -e .
```

### Building Your Own Agent
Amnesic is a substrate for specialized agents. Create a mission and point it at a directory:

```python
from amnesic import AmnesicSession

# 1. Define Persona/Strategy
strategy = "PERSONA: Security Auditor. PRIORITY: Find hardcoded secrets."

# 2. Initialize Session
session = AmnesicSession(
    mission="Audit the ./src directory for vulnerabilities.",
    root_dir="./src",
    strategy=strategy,
    l1_capacity=2000
)

# 3. Execute
session.visualize() # Show the Graph
session.run()
```

## Verification

To verify the protocol's integrity and the "One-File" bottleneck, run the suite:

```bash
bash run_all_tests.sh
```

### Test Suite Manifest
You can also run individual capability proofs to see specific features in action:

| Script | Capability Proven |
| :--- | :--- |
| `tests/proofs/basic_semantic_proof.py` | **Cross-File Retrieval:** Retrieval & Amnesia Mechanics. |
| `tests/proofs/advanced_semantic_proof.py` | **Dynamic Logic:** Heuristic matching & dynamic rules. |
| `tests/proofs/proof_code_basic.py` | **Code Patching:** Single-file bug fixing. |
| `tests/proofs/proof_code_advanced.py` | **Architectural Refactor:** Multi-file synchronization. |
| `tests/proofs/proof_contracts.py` | **Contract Enforcement:** Spec vs. Implementation validation. |
| `tests/proofs/proof_gc.py` | **Structural GC:** Dumping orphaned context. |
| `tests/proofs/proof_isolation.py` | **Failure Isolation:** Safe speculation. |
| `tests/proofs/proof_time_travel.py` | **State Snapshotting:** Reasoning about past states. |
| `tests/proofs/proof_hive_mind.py` | **State Sync:** Multi-Agent knowledge sync. |
| `tests/proofs/proof_ignorance.py` | **Ignorance Detection:** Identifying missing deps. |
| `tests/proofs/proof_cognitive_load.py` | **Cognitive Load:** Filtering noise for focus. |
| `tests/proofs/proof_determinism.py` | **Determinism:** Repeatable decision making. |
| `tests/proofs/proof_elastic_context.py` | **Elastic Context:** Flexible multi-document management. |
| `tests/proofs/proof_self_correction.py` | **Self-Correction:** Updating memory based on new evidence. |
| `tests/proofs/proof_marathon.py` | **Marathon Session:** Sustained reasoning over 50+ turns. |
| `tests/proofs/proof_extreme_efficiency.py` | **Extreme Efficiency:** Operating in < 512 token L1. |
| `tests/proofs/proof_workspace_nexus.py` | **Workspace Nexus:** Cross-repository reasoning and fixing. |
| `tests/proofs/proof_model_invariance.py` | **Model Invariance:** Stable reasoning across model sizes via driver healing. |
| `tests/proofs/proof_failure_taxonomy.py` | **Failure Safety:** Controlled degradation (Deadlock/Thrash) with automated recovery. |
| `tests/proofs/proof_human_friction.py` | **Human Friction:** "Verify-First" protocol to detect and report state corruption. |
| `tests/proofs/proof_persona_swap.py` | **Strategy Switching:** Multi-phase execution workflow. |
| `tests/proofs/proof_comparator.py` | **Comparator:** Dual-Slot L1 comparison mechanics. |
| `tests/proofs/proof_prefetch.py` | **Context Prefetch:** Predictive background staging. |
| `tests/proofs/proof_clean_room.py` | **Data Sanitization:** IP Sanitization & Secret Redaction. |
| `tests/proofs/proof_rosetta.py` | **Legacy Migration:** Schema-driven Legacy Migration. |
| `tests/proofs/real_stress_test.py` | **LRU Stress Test:** Automatic eviction on overflow. |
| `tests/control_proofs/control_basicsemantic_proof.py` | **Control Group:** Baseline failure demonstration. |

## Experimental / Roadmap
*   **Real-time context sharing:** Between concurrent agents.
*   **State rollback on test failure:** Automatic state reversion after failed verification steps.
