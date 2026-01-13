# Amnesic Protocol

**Amnesic** is a context-management protocol for LLM agents. It enables reliable long-horizon reasoning by physically preventing "Context Drift." It treats the LLM context window as disposable RAM and forces all permanent knowledge into structured **Artifacts**.

## 30-Second Quickstart

```python
from amnesic import AmnesicSession

# 1. Initialize a session with a strictly bounded context (e.g., 2000 tokens)
session = AmnesicSession(
    mission="Find the bug in ./src/logic.py and fix it.",
    root_dir="./src",
    l1_capacity=2000
)

# 2. Run the amnesic loop (Map -> Read -> Extract -> Commit -> Forget)
session.run()
```

## The Amnesic Rules (Plain English)

1.  **Explicit Context Control:** The agent's focus is a choice. Data is explicitly staged and just as explicitly ejected.
2.  **Take good notes (The Backpack):** Before moving to a new task, the agent must save important facts as **Artifacts**.
3.  **Wipe the slate clean:** Once a fact is saved, the raw source text is wiped from context. No history, no clutter.
4.  **Verify before acting:** Every move is checked by a **Validator** to ensure rules are followed and no hallucinations occur.

---

## Why this exists: Correctness > Fluency

Standard agents fail at long tasks because their "chat history" gets too long and noisy. **Amnesic** replaces history with **Authoritative State**.

| Feature | Standard ReAct | Amnesic Protocol |
| :--- | :--- | :--- |
| **Memory** | Opaque Chat History | Structured Artifact Store |
| **Integrity** | Prone to Drift | Physically Immune to History Poisoning |
| **Trust** | Prompt-based instructions | Validator-enforced Invariants |

---

## Core Concepts

### 1. Authoritative State (AST)
Code is not prose. Amnesic uses **Abstract Syntax Trees** to extract "Semantic Skeletons" of your code. This allows the agent to throw away raw text but still "know" your function signatures and dependencies.

### 2. The Physical Validator (Auditor)
The Auditor checks every move *before* it happens. If the model tries to "hallucinate" a success or violate a file-system constraint, the move is physically blocked.

---

## Advanced Usage

### 1. Building Your Own Agent
Amnesic is a substrate for specialized cognitive personalities. Use **Strategies** to define how the agent extracts data.

```python
from amnesic import AmnesicSession

# 1. Define a Persona/Strategy
strategy = "PERSONA: Security Auditor. PRIORITY: Find hardcoded keys."

# 2. Initialize Session
session = AmnesicSession(
    mission="Audit the ./src directory for secrets.",
    root_dir="./src",
    strategy=strategy,
    l1_capacity=4000
)

session.run()
```

### 2. Custom Context Management (Elastic Mode)
By default, Amnesic enforces a **Strict One-File** policy. For tasks requiring cross-document reasoning, enable **Elastic Mode**.

```python
# Allows multiple files to coexist in context up to the token limit
session = AmnesicSession(..., elastic_mode=True)
```

### 3. Eviction Policies & Document Purging
You can inject deterministic rules to force context wipes based on specific state conditions.

```python
from amnesic.core.policies import KernelPolicy

# Force-purge context if a 'THREAT' artifact is found
purge_policy = KernelPolicy(
    name="EmergencyWipe",
    condition=lambda state: any("THREAT" in a.identifier for a in state.artifacts),
    reaction=lambda state: ManagerMove(
        thought_process="Threat detected. Wiping context.",
        tool_call="unstage_context",
        target="ALL"
    )
)

session = AmnesicSession(..., policies=[purge_policy])
```

---

## Detailed Documentation
- [Failure Taxonomy](FAILURE_TAXONOMY.md): Named failure modes we solve.
- [Presets Guide](PRESETS_GUIDE.md): Build specialized Security or Refactor agents.
- [Core Specification](AMNESIC_CORE_SPEC.md): The irreducible laws of the protocol.

## Installation
```bash
pip install -e .
# Requires Ollama running locally (default: rnj-1:8b-cloud)
```

## Running Proofs
```bash
# Run the full defensibility benchmark
python tests/comparative/run_suite.py
```