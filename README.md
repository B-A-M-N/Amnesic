# Amnesic Protocol

**Amnesic** is a context-management protocol that enables Large Language Models (LLMs) to perform complex, long-horizon software engineering tasks with high reliability. It achieves this by replacing the traditional "chat history" with a rigorous system of **Explicit State** and **Physical Invariants**.

Unlike standard agents that "drift" as their context window fills with noise, an Amnesic agent treats its context window as disposable RAM. It must explicitly "learn" (extract artifacts) and "forget" (clear context) to maintain perfect focus over thousands of steps.

---

## 🚀 The Core Philosophy

1.  **Amnesia is a Feature:** The agent's memory is wiped after every significant action. This forces it to externalize all necessary information into structured **Artifacts** (The Backpack).
2.  **Physical Invariants:** Safety and correctness are enforced by code, not just prompts. If an agent tries to read a file without clearing its memory, the system *physically blocks* the action.
3.  **The Trinity Architecture:**
    *   **Manager (The Brain):** The LLM that decides *what* to do.
    *   **Auditor (The Conscience):** A deterministic policy engine that decides if the move is *safe* and *relevant*.
    *   **Executor (The Hands):** The code that actually touches the file system.

---

## ⚡ Quickstart

### Installation

```bash
pip install -e .
# Requires an Ollama server running locally (default model: rnj-1:8b-cloud)
```

### Basic Usage

```python
from amnesic import AmnesicSession

# Initialize a session with strict boundaries
session = AmnesicSession(
    mission="Read src/config.py to find the API key variable name, then update src/main.py to use it.",
    root_dir="./src",
    l1_capacity=2000  # Restrict context to 2k tokens to force efficiency
)

# Run the autonomous loop
session.run()
```

---

## 🧠 Key Capabilities

Amnesic enables workflows that are impossible for standard "chat" agents:

### 1. Infinite Horizon (Marathon Mode)
Process datasets infinitely larger than the context window.
*   **How:** The agent processes one file, extracts the relevant data to the Sidecar (Backpack), and then *forgets* the file before opening the next.
*   **Proof:** `tests/proofs/proof_native_overflow.py` (Processed 40k tokens of data with a 25k limit).

### 2. Semantic Self-Correction
The agent can update its own knowledge base when it encounters contradictory information.
*   **How:** If File B contradicts File A, the agent updates the specific Artifact in the Backpack without needing to re-read File A.
*   **Proof:** `tests/proofs/proof_self_correction.py`

### 3. Context & Persona Swapping
Pass the "brain" of one agent to another, or switch strategies mid-flight.
*   **How:** Since state is externalized (Artifacts), a "Scout" agent can map a repo and die. A "Coder" agent can then wake up, inherit the Scout's Backpack, and start coding immediately without re-reading the repo.
*   **Proof:** `tests/proofs/proof_context_offloading.py`

### 4. Clean Room Sanitization
Extract logic from sensitive files without leaking secrets.
*   **How:** The agent reads the secret file, writes a "stub" (redacted) version to disk, and then must *physically unstage* the secret file before it is allowed to report success.
*   **Proof:** `tests/proofs/proof_clean_room.py`

### 5. Context Normalization (Scaling Small Models)
Enable smaller models to punch above their weight.
*   **How:** By acting as a "Staging Normalizer," Amnesic virtualizes infinite context. A 7B model with a small window can process massive datasets by seeing them as a stream of perfectly-sized chunks, effectively emulating the infinite-context performance of much larger models.

---

## 🛠️ The Toolkit

The Manager has access to a specialized set of tools designed for this protocol:

*   `stage_context(path)`: Load a file into L1 RAM. (Triggers auto-eviction of previous file in Strict Mode).
*   `save_artifact(ID: value)`: Save a snippet, fact, or decision to the Backpack.
*   `unstage_context(path)`: Explicitly clear a file from RAM.
*   `write_file(path: content)`: Create or overwrite a file.
*   `edit_file(path: instruction)`: Surgically edit a file using AI.
*   `calculate(expression)`: Perform math or combine artifacts (e.g., `calculate(SUM_BACKPACK)`).
*   `switch_strategy(name)`: Change the active persona (e.g., from "Architect" to "Implementer").
*   `halt_and_ask(result)`: Declare the mission complete.

---

## 📖 Advanced Workflows

### Elastic Mode (Multi-File Context)
Sometimes you *need* to see two files at once (e.g., comparing a config to usage).
```python
session = AmnesicSession(..., elastic_mode=True)
# The agent can now stage multiple files up to the l1_capacity limit.
```

### Custom Audit Profiles
Control how strict the Auditor is.
*   **STRICT_AUDIT (Default):** Paranoiac. Every action is double-checked by an LLM. High cost, max safety.
*   **FLUID_READ:** heuristic-based checks for reading files (fast), LLM checks for writing (safe).
*   **HIGH_SPEED:** Minimal checks. For trusted environments only.

```python
session = AmnesicSession(..., audit_profile="FLUID_READ")
```

### Pipelines (Map-Reduce)
Chain agents together for complex tasks.
```python
from amnesic.core.pipeline import AmnesicPipeline

pipeline = AmnesicPipeline()
# Step 1: Scout scans for files
pipeline.add_step("Scout", "Scan src/ and save a list of all .py files as FILE_LIST.")
# Step 2: Workers process each file in parallel (conceptually)
pipeline.add_map_step("Analyzer", "FILE_LIST", "Analyze {item} for security vulnerabilities.")
# Step 3: Reporter aggregates results
pipeline.add_step("Reporter", "Combine all vulnerability reports into final_report.md.")

pipeline.run()
```

---

## 🛡️ Safety & Limitations

*   **Speed:** Amnesic is slower than standard agents because it performs more "thinking" steps (staging, saving, verifying).
*   **Prompt Overhead:** The system prompts are complex to enforce these invariants, consuming ~1k tokens per turn.
*   **Model Requirements:** Works best with models that follow instructions well (e.g., Qwen 2.5 Coder, Llama 3). We have hardened it for 8B models, but larger models yield better reasoning.

For a deep dive into the architecture, failure taxonomy, and specifications, see [DOCS.md](DOCS.md).
