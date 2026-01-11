# Amnesic: Context Offloading Protocol

**Amnesic** is a context-management framework for LLM agents that enables reliable long-horizon reasoning and code modification by enforcing strict context staging and persistent semantic state extraction.

Amnesic enables agents to operate over unbounded information while maintaining a strictly bounded context window. It achieves this by treating the context window as a volatile staging area and persistently storing only extracted semantic and structural state in an external "Sidecar."

## Core Philosophy

Standard agents suffer from **Context Drift**: as the conversation grows, reasoning degrades, costs increase, and earlier instructions are lost in the noise.

**Amnesic does not eliminate semantic drift; it contains it** by forcing all long-term knowledge into explicit, inspectable state transitions instead of implicit conversational history.

Amnesic solves drift by implementing a **Memory Management Unit (MMU)** logic similar to an Operating System:
*   **L1 Cache (Context Window):** Expensive, extremely limited, volatile. Only holds the *immediate* file or data fragment being analyzed.
*   **L2/L3 Storage (Artifacts & Vectors):** Cheap, persistent, unlimited. Holds the *extracted insights*, contracts, and decisions.

**The Protocol:**
> "Map. Read. Extract. Commit. Forget."

## System Architecture

The framework is implemented as a **LangGraph** deterministic state machine, ensuring persistent state across turns via a checkpointing system.

*   **The Mapper (HAL):** Performs real-time Structural AST scans and Vector Indexing to provide the agent with "Physical Truth" of the environment.
*   **The Manager (CPU):** Decides moves based on the L1 view and "Shared Ground Truth" (Artifacts).
*   **The Pager (MMU):** Enforces the **Strict Amnesic Bottleneck** (e.g., 1500 tokens). Manages L1 loading, auto-eviction, and **L2 Prefetching** for background staging.
*   **The Comparator (FPU):** A specialized "Dual-Slot" controller for `diff` and `merge` tasks. Temporarily allows two files in L1 while enforcing a strict "Double Eviction" cleanup.
*   **The Auditor (Kernel)::** Intercepts and validates every move against semantic contracts and structural invariants.

---

## Specialized Workflows (Presets)

Amnesic includes specialized presets for high-stakes enterprise tasks:

### 1. The Clean Room (PII & IP Sanitization)
Ensures that an agent can ingest highly sensitive proprietary data (L1), extract the sanitized logic or public interface (Artifact), and permanently discard the sensitive context.
*   *Verification:* `tests/proofs/proof_clean_room.py`

### 2. The Rosetta Stone (Legacy Migration)
Migrates "Spaghetti" legacy code (e.g., COBOL-style patterns) into clean, modern architectures by strictly following a "Schema Artifact" while architecturally forbidden from preserving legacy naming or global state.
*   *Verification:* `tests/proofs/proof_rosetta.py`

---

## Proven Capabilities

The following capabilities are verified in the regression suite. Detailed traces are available in [PROVEN_LOGS.md](PROVEN_LOGS.md).

### 1. Semantic Intelligence & Retrieval
*   **The Island Hop:** Success in retrieving $X$ from File A and $Y$ from File B, then summing them, while architecturally forbidden from holding both in memory.
*   **Blind Logic Discovery:** Agent enters a system with 0 knowledge, discovers a hidden math rule (`ADD/MUL/DIV`) in a "Logic Gate" file, and applies it to hidden data.
*   **Intent Recovery:** Successfully extracts data from "Lying Variables" (e.g., finding `VAL_A` inside a variable named `not_val_a`) by prioritizing structural intent over string similarity.

### 2. Code Engineering
*   **Junior Dev Fix:** Identifies and surgically patches hardcoded bugs in a single turn.
*   **The Breaking Change:** Performs multi-file architectural refactoring (e.g., updating an API signature in `api.py` and propagating the change to all call sites in `client.py`) without holding both files in context.

### 3. Memory Infrastructure
*   **Structural GC (Garbage Collection):** Proactively detects when a file becomes semantically unreachable after a refactor and dumps it to save cognitive load.
*   **Automated LRU Eviction:** The Pager automatically purges the Least Recently Used (LRU) context when the token budget is exceeded.
*   **L2 Prefetching (Predictive Staging):** Allows the Manager to stage the *next* predicted file into RAM (L2) while the Agent is still processing the current file in L1, eliminating "Page Fault" latency.
*   **Dual-Slot Comparison:** Enables semantic `diff` operations by safely holding two versions of a file in L1, with a guaranteed "Amnesic Wipe" once the comparison artifact is generated.
*   **Time Travel (Versioning):** Snapshots the agent's "understanding" at a specific point in time. Agent can correctly explain a past bug even after the code on disk has been fixed.
*   **The Hive Mind (Sync):** Two distinct agent instances sharing a single Sidecar. Agent B knows what Agent A learned without performing any File I/O.

### 4. Governance & Reliability
*   **Contract Enforcement:** Validates implementation code against a "Contract Artifact" (spec) and halts on violations (e.g., wrong return type).
*   **Failure Isolation:** Speculative changes are quarantined in a hypothesis layer; destructive failures do not poison the main codebase.
*   **Ignorance Detection:** Identifies missing dependencies (e.g., an import to a non-existent file) and explicitly halts to ask for context instead of hallucinating.

### 5. Security & Hardening (Kernel Level)
*   **The Path Jail:** Enforces strict chroot-like isolation. Agent is architecturally forbidden from accessing files outside the approved `root_dirs`.
*   **Physical Pre-Flight:** Intercepts security violations (traversal, sensitive files) in the session logic *before* calling the LLM, preventing prompt-injection jailbreaks.
*   **Payload Protection:** Validates and caps generated content size (1MB) to prevent system memory saturation from massive hallucinations.
*   **Hardware-Enforced Context:** Strictly enforces the `l1_capacity` at the driver level (e.g., `num_ctx`), ensuring the model literally cannot "see" beyond the amnesic window.

### 6. Agent Dynamics & Strategy
*   **The Jekyll & Hyde Protocol (Persona Swap):** The agent dynamically switches strategies mid-session. It starts as an **Architect** to plan a complex refactor ("The Spaghetti Decomposition") and then transforms into an **Implementer** to execute it surgically.
*   **Interference Resistance:** Outperforms standard ReAct agents which loop or fail under the same context window constraints.

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
session.visualize() # Show the Kernel graph
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
| `tests/proofs/basic_semantic_proof.py` | **The Island Hop:** Retrieval & Amnesia Mechanics. |
| `tests/proofs/advanced_semantic_proof.py` | **Blind Logic:** Intent Recovery & Dynamic Rules. |
| `tests/proofs/proof_code_basic.py` | **Code Patching:** Surgical bug fixing. |
| `tests/proofs/proof_code_advanced.py` | **Architectural Refactor:** Multi-file synchronization. |
| `tests/proofs/proof_contracts.py` | **Contract Enforcement:** Spec vs. Implementation validation. |
| `tests/proofs/proof_gc.py` | **Structural GC:** Dumping orphaned context. |
| `tests/proofs/proof_isolation.py` | **Failure Isolation:** Safe speculation. |
| `tests/proofs/proof_time_travel.py` | **Time Travel:** Reasoning about past states. |
| `tests/proofs/proof_hive_mind.py` | **Hive Mind:** Multi-Agent knowledge sync. |
| `tests/proofs/proof_ignorance.py` | **Ignorance Detection:** Identifying missing deps. |
| `tests/proofs/proof_cognitive_load.py` | **Cognitive Load:** Filtering noise for focus. |
| `tests/proofs/proof_determinism.py` | **Determinism Levers:** Repeatable decision making. |
| `tests/proofs/proof_elastic_context.py` | **Elastic Context:** Flexible multi-document management. |
| `tests/proofs/proof_self_correction.py` | **Self-Correction:** Updating memory based on new evidence. |
| `tests/proofs/proof_marathon.py` | **Marathon Session:** Sustained reasoning over 50+ turns. |
| `tests/proofs/proof_extreme_efficiency.py` | **Extreme Efficiency:** Operating in < 512 token L1. |
| `tests/proofs/proof_extreme_efficiency.py` | **Extreme Efficiency:** Hardware-enforced Micro-Kernel. |
| `tests/proofs/proof_workspace_nexus.py` | **Workspace Nexus:** Cross-repository reasoning and fixing. |
| `tests/proofs/proof_model_invariance.py` | **Model Invariance:** Equivalent results across different LLMs. |
| `tests/proofs/proof_failure_taxonomy.py` | **Failure Safety:** Controlled degradation under stress. |
| `tests/proofs/proof_human_friction.py` | **Human Friction:** Catching manual artifact corruption. |
| `tests/proofs/proof_persona_swap.py` | **Persona Swap:** Architect -> Implementer workflow. |
| `tests/proofs/proof_comparator.py` | **Comparator:** Dual-Slot L1 comparison mechanics. |
| `tests/proofs/proof_prefetch.py` | **L2 Prefetch:** Predictive background staging. |
| `tests/proofs/proof_clean_room.py` | **Clean Room:** IP Sanitization & Secret Redaction. |
| `tests/proofs/proof_rosetta.py` | **Rosetta Stone:** Schema-driven Legacy Migration. |
| `tests/proofs/real_stress_test.py` | **LRU Stress Test:** Automatic eviction on overflow. |
| `tests/control_proofs/control_basicsemantic_proof.py` | **Control Group:** Baseline failure demonstration. |

## Experimental / Roadmap
*   **Swarm Memory:** Real-time L1 sharing between concurrent agents.
*   **Diff-Aware Epistemology:** Automatic sidecar rollbacks on failed test runs.