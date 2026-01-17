# Developer Guide: Creating Amnesic Presets

An **Amnesic Preset** is a specialized cognitive configuration of the framework. It defines how the agent should behave, what knowledge it starts with, and what constraints it must respect.

Because the core architecture is stateless, a "Preset" is simply a way to pre-configure the **Mission**, **Artifacts**, and **Tools** for a specific domain.

---

## Core Pattern: Cognitive Inheritance

All presets must inherit from `AmnesicSession`. This ensures they have access to the LangGraph coordination, the Dynamic Pager (L1 Memory), and the Auditor.

### 1. Basic Structure
Create a new file in `amnesic/presets/your_preset.py`:

```python
from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

class MyCustomSession(AmnesicSession):
    def __init__(self, mission: str, **kwargs):
        # 1. Define the Behavioral Protocol
        custom_constraints = (
            "PROTOCOL_X ACTIVE: \n"
            "1. Priority A...\n"
            "2. Constraint B..."
        )
        full_mission = f"{mission}\n\n{custom_constraints}"
        
        # 2. Initialize the Base Session
        super().__init__(mission=full_mission, **kwargs)
        
        # 3. Inject Domain Knowledge (Optional)
        self.state['framework_state'].artifacts.append(
            Artifact(
                identifier="KNOWLEDGE_BASE",
                type="config",
                summary="Standard operating procedure for this task...",
                status="verified_invariant"
            )
        )
```

---

## The Four Levers of a Preset

### Lever 1: The Behavioral Protocol (The Prompt)
This is the most powerful tool. By injecting "Infrastructure Truth" into the `mission`, you change how the Manager decides and how the Auditor judges.
*   **Use for:** Security constraints, coding styles, or logical workflows (e.g., "Verify before Writing").

### Lever 2: Invariant Artifacts (The "Backpack")
Artifacts added during `__init__` are "Permanent Memory." The agent will see these in every turn and treat them as ground truth.
*   **Use for:** API schemas, database DDLs, or compliance checklists.

### Lever 3: Specialized Tools
You can override `_setup_default_tools` to add or modify capabilities specific to the preset.

```python
def _setup_default_tools(self):
    super()._setup_default_tools()
    # Add a custom tool
    self.tools.register_tool("run_security_scan", self._tool_scan)

def _tool_scan(self, target: str):
    # Implementation logic here...
    self.state['framework_state'].last_action_feedback = "Scan Complete: 0 vulnerabilities."
```

### Lever 4: Audit Profiles
You can control the "paranoia level" of your preset by configuring the `audit_profile`.

*   **STRICT_AUDIT (Default):** Every move is double-checked by an LLM. Use for: Writing code, deleting files, managing secrets.
*   **FLUID_READ:** Skips the LLM check for read-only actions if they are relevant. Use for: Scouting, Code Analysis, Search Agents.
*   **HIGH_SPEED:** Fast for almost everything except critical system files. Use for: Prototyping.

### Advanced: Custom Audit Profiles
If the default profiles are too rigid, you can define your own.

```python
from amnesic.core.audit_policies import AuditProfile

# A profile that allows saving artifacts without nagging, but blocks all edits
LAX_OFFLOAD = AuditProfile(
    name="LAX_OFFLOAD",
    fast_path_actions=["save_artifact", "stage_context"],
    relevance_threshold=0.2,
    strict_actions=["write_file", "edit_file"]
)

class DataMiningSession(AmnesicSession):
    def __init__(self, mission: str, **kwargs):
        super().__init__(
            mission=mission,
            audit_profile="LAX_OFFLOAD", # Start in this mode
            custom_audit_profiles={"LAX_OFFLOAD": LAX_OFFLOAD}, # Register it
            **kwargs
        )
```

```python
class ScoutSession(AmnesicSession):
    def __init__(self, mission: str, **kwargs):
        # Starts in FLUID mode for fast analysis
        super().__init__(
            mission=mission, 
            audit_profile="FLUID_READ",
            **kwargs
        )
```

---

## Example: The "Refactor" Preset
This preset focuses on cleaning code without changing behavior.

```python
class RefactorSession(AmnesicSession):
    def __init__(self, mission: str, **kwargs):
        protocol = (
            "REFACTORING MODE: \n"
            "1. You must not change the external API or logic.\n"
            "2. You must apply PEP8 styling.\n"
            "3. Every function must have a type-hinted signature."
        )
        super().__init__(mission=f"{mission}\n\n{protocol}", **kwargs)
        
        # Injected Best Practices
        self.state['framework_state'].artifacts.append(
            Artifact(identifier="LINT_RULES", type="style", summary="Max line length: 88.")
        )
```

---

## How to Verify Your Preset
Always create a **Proof** file in `tests/proofs/proof_your_preset.py`.

1.  **Define a Scenario:** Create a temporary file that represents the "messy" input.
2.  **Initialize Preset:** Instantiate your `CustomSession`.
3.  **Run Stream:** Let the agent process the task.
4.  **Audit Output:** Programmatically check if the final Artifacts or files meet the preset's requirements (e.g., checking if secrets were redacted in a Clean Room).

---

## Why This is Safe
Presets are **additive**. They do not modify `amnesic/core/session.py`. This means:
*   Standard tests will always pass.
*   The "Amnesic Kernel" remains stable while you build complex personalities on top of it.
*   You can mix and match presets via composition (e.g., a `CleanRoomRefactorSession`).

```