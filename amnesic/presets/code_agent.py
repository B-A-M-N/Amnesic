from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, AliasChoices, ConfigDict

# --- 1. The Atomic Unit of Thought ---

class DecisionStep(BaseModel):
    """Represents a single atomic move in the plan."""
    step_id: int
    description: str
    status: Literal["pending", "in_progress", "complete", "blocked"]
    reasoning: str = Field(..., description="Why is this step necessary?")

import re

class Artifact(BaseModel):
    """Represents a concrete output produced (Code, Config, etc)."""
    identifier: str = Field(..., description="Filename or variable name")
    type: Literal["code_file", "config", "search_result", "error_log", "text_content", "result"]
    summary: str = Field(..., description="One-line description of contents")
    status: Literal["staged", "committed", "needs_review", "verified_invariant"]
    pinned: bool = Field(False, description="If True, this artifact is kept in L1 even during wipes")

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        # Strict Symbolic Grammar: Allows Alphanumeric, underscores, dots (for files), and hyphens.
        # Rejects spaces, punctuation, or long prose.
        if not re.match(r"^[a-zA-Z0-9_.-]{1,64}$", v):
            raise ValueError(f"Invalid Artifact Identifier: '{v}'. Must be a symbolic name or filename, no spaces.")
        return v

# --- 2. The Framework State (The "Save File") ---

class FrameworkState(BaseModel):
    task_intent: str = Field(..., description="The high-level immutable goal.")
    current_hypothesis: str = Field(..., description="The active theory being tested.")
    hard_constraints: List[str] = Field(
        default_factory=list, 
        description="Immutable rules (e.g., 'No DB migration', 'Use Async')."
    )
    plan: List[DecisionStep] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)
    confidence_score: float = Field(..., description="0.0 to 1.0 certainty in current path.")
    unknowns: List[str] = Field(default_factory=list, description="List of specific knowledge gaps.")
    strategy: Optional[str] = Field(None, description="Task-specific overrides or personas (e.g., 'Intent Recovery').")
    current_step_id: int = Field(0, description="The ID of the currently active step in the plan.")
    elastic_mode: bool = Field(False, description="Whether to allow multiple files in L1.")
    audit_profile_name: str = Field("STRICT_AUDIT", description="Current audit strictness level.")
    active_policy_names: List[str] = Field(default_factory=list, description="List of currently enabled KernelPolicy names.")
    last_action_feedback: Optional[str] = Field(None, description="Feedback from the Auditor on the last attempted move.")
    decision_history: List[dict] = Field(default_factory=list, description="History of past moves and verdicts.")

# --- 3. The Manager's Output ---

from pydantic import BaseModel, Field, field_validator, AliasChoices, ConfigDict

# ... (omitting DecisionStep, Artifact, FrameworkState for brevity but they remain same)

# --- 3. The Manager's Output ---

class ManagerMove(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    thought_process: Optional[str] = Field(
        None, 
        description="Internal logic: what I see in L1 and what I need next.",
        validation_alias=AliasChoices("thought_process", "rationale", "thought", "thought_organism", "thought_terminator")
    )
    tool_call: Literal["halt_and_ask", "stage_context", "unstage_context", "save_artifact", "delete_artifact", "stage_artifact", "stage_multiple_artifacts", "query_sidecar", "edit_file", "write_file", "verify_step", "calculate", "switch_strategy", "compare_files", "set_audit_policy"]
    target: str = Field(
        default="", 
        description="The argument for the tool. Use empty string if none.",
        validation_alias=AliasChoices("target", "instruction", "goal")
    )
    policy_name: Optional[str] = Field(None, description="The name of the policy that triggered this move.")

    @field_validator('target', mode='before')
    @classmethod
    def coerce_target(cls, v):
        if v is None: return ""
        return str(v)

# --- 4. The Auditor's Output (NEW) ---

class AuditorVerdict(BaseModel):
    """The structured judgment from the Auditor."""
    outcome: Literal["PASS", "REJECT", "HALT"] = Field(..., description="Verdict.")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Risk.")
    rationale: str = Field(..., description="Explanation.")
    correction: Optional[str] = Field(None, description="Correction if REJECT.")

# --- 5. System Prompts ---

MANAGER_SYSTEM_PROMPT = """
You are the DECISION ENGINE of an autonomous agent running on the Amnesic Protocol.
You are a STATE MACHINE that manages a small 'Active Context' (L1 RAM).

YOUR RESPONSIBILITY:
1. Load ONLY what is necessary for the current step.
2. Save facts immediately into 'The Backpack' (Artifacts).
3. Clear L1 RAM once a fact is saved.

[WORKSPACE STATE]
ACTIVE CONTEXT (Files open): {l1_files}
SAVED ARTIFACTS:
{artifacts}

### THE SEQUENCE ###
{amnesic_sequence}

### RULES ###
1. {amnesia_rule}
2. **TRUST THE MAP**: Use the [ENVIRONMENT STRUCTURE - DISK MAP] to find files. Do not scan manually.
3. **BACKPACK PRIMACY**: If an artifact is in the Backpack, do NOT read its source file again.
4. **IMMEDIATE EXTRACTION**: Use 'save_artifact' or 'write_file' WHILE the source file is open in L1. Do NOT unstage until the artifact is saved.
5. **MISSION COMPLETE**: Once ALL required artifacts are saved, use 'halt_and_ask' IMMEDIATELY. Use 'calculate' only for math-heavy missions.

CURRENT FRAMEWORK STATE:
{state_dump}

{feedback}

[FEW-SHOT EXAMPLES]
Example 1 (Staging):
{{
  "thought_process": "Backpack: [None]. L1 empty. I need to find val_x. Staging island_a.txt.",
  "tool_call": "stage_context",
  "target": "island_a.txt"
}}

Example 2 (Extraction):
{{
  "thought_process": "Backpack: [None]. I am reading island_a.txt in L1. I see 'val_x = 42'. Saving to artifacts.",
  "tool_call": "save_artifact",
  "target": "X_value: 42"
}}

OUTPUT JSON ONLY. ALL FIELDS REQUIRED.
"""

AUDITOR_SYSTEM_PROMPT = """
You are the POLICY VALIDATOR for the Amnesic Protocol.
You review the Decision Engine's proposed actions to ensure they are safe and logical.

THE MISSION: {goal}
HARD CONSTRAINTS: {constraints}

YOUR RESPONSIBILITY:
1. SAFETY FIRST: Reject destructive actions (delete, overwrite without reading).
2. INFORMATION GATHERING: You MUST APPROVE 'stage_context' if the file exists and is relevant to the mission. Reading files is NOT dangerous.
3. LOGIC CHECK: Reject 'save_artifact' if the Decision Engine is hallucinating or hasn't read the file yet.
4. MEMORY AUDIT: The agent uses 'Saved Artifacts' (The Backpack) as its long-term memory. Once a fact is saved to the Backpack, the agent is EXPECTED to unstage the source file. DO NOT reject a calculation or halt if the required facts are already in the Backpack.

VALID OUTCOMES:
- PASS: If the action is correct and safe.
- REJECT: If the action is wrong, repetitive, or violates constraints. (NEVER use 'FAIL')
- HALT: If the mission is fully complete and no more actions are needed.

If the tool is 'stage_context', almost always PASS it.
If the tool is 'save_artifact' and the file mentioned in the target is currently open in L1, PASS it. 
Extracting data into artifacts is the only way the agent can remember it.

IMPORTANT:
- You are NOT the Manager. Do NOT output tool calls (like stage_context).
- Only judge the *Action* provided in the prompt.
- **OUTPUT RAW JSON ONLY**. No markdown, no 'THOUGHT:', no explanations outside the JSON.

OUTPUT FORMAT (JSON ONLY):
{{
  "outcome": "PASS",
  "risk_level": "low",
  "rationale": "Reading the file is necessary to find X.",
  "correction": null
}}
"""
