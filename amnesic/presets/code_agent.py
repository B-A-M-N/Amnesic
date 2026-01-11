from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

# --- 1. The Atomic Unit of Thought ---

class DecisionStep(BaseModel):
    """Represents a single atomic move in the plan."""
    step_id: int
    description: str
    status: Literal["pending", "in_progress", "complete", "blocked"]
    reasoning: str = Field(..., description="Why is this step necessary?")

class Artifact(BaseModel):
    """Represents a concrete output produced (Code, Config, etc)."""
    identifier: str = Field(..., description="Filename or variable name")
    type: Literal["code_file", "config", "search_result", "error_log", "text_content", "result"]
    summary: str = Field(..., description="One-line description of contents")
    status: Literal["staged", "committed", "needs_review", "verified_invariant"]

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
    elastic_mode: bool = Field(False, description="Whether to allow multiple files in L1.")
    last_action_feedback: Optional[str] = Field(None, description="Feedback from the Auditor on the last attempted move.")
    decision_history: List[dict] = Field(default_factory=list, description="History of past moves and verdicts.")

# --- 3. The Manager's Output ---

class ManagerMove(BaseModel):
    thought_process: str = Field(..., min_length=10, description="Internal logic: what I see in L1 and what I need next.")
    tool_call: Literal["stage_context", "unstage_context", "save_artifact", "delete_artifact", "stage_artifact", "edit_file", "write_file", "halt_and_ask", "verify_step", "calculate", "switch_strategy", "compare_files"]
    # [CRITICAL FIX] Default to empty string to prevent validation crashes
    target: str = Field(default="", min_length=0, description="The argument for the tool. Use empty string if none.")

# --- 4. The Auditor's Output (NEW) ---

class AuditorVerdict(BaseModel):
    """The structured judgment from the Auditor."""
    outcome: Literal["PASS", "REJECT", "HALT"] = Field(..., description="Verdict.")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Risk.")
    rationale: str = Field(..., description="Explanation.")
    correction: Optional[str] = Field(None, description="Correction if REJECT.")

# --- 5. System Prompts ---

MANAGER_SYSTEM_PROMPT = """
You are the KERNEL of an autonomous agent running on the Amnesic Framework.
You are NOT a chat bot. You are a STATE MACHINE.

YOUR RESPONSIBILITY:
1. Manage the 'L1 Cache' (Context Window). It is small and expensive.
2. Only load what is immediately necessary for the Current Step.
3. Update the Framework State after every action.

AVAILABLE TOOLS:
{tools_available}

TOOL DESCRIPTIONS:
- stage_context(path): Load a FILE from disk into L1 RAM.
- unstage_context(path): Remove a FILE from L1 RAM.
- save_artifact(key): Extract data from L1 RAM and save to persistent storage.
- stage_artifact(key): Load a previously saved ARTIFACT back into L1 RAM.
- delete_artifact(key): Permanently remove an artifact (also wipes L1).
- edit_file(path: instr): Apply a surgical code patch.
- write_file(path: content): Create a new file.
- switch_strategy(persona): Change your operating mode.
- halt_and_ask(result): Mission complete.

[WORKSPACE STATE]
CURRENT L1 CACHE (Files currently open): {l1_files}
SWAP SPACE (Files on disk): {l2_files}
SAVED ARTIFACTS:
{artifacts}

{feedback}

[STRICT RULES]
1. {amnesia_rule}
2. EXTRACT BEFORE FORGET: If you are reading a file and find mission-critical data, you MUST use 'save_artifact' BEFORE you 'unstage_context'. If you unstage without saving, you will FORGET the data.
3. You are FORBIDDEN from using 'stage_context' on a file that is already in L1.
4. If you have found the data you need (X or Y), you MUST save it as an ARTIFACT using 'save_artifact' immediately.
5. {eviction_rule}
6. SEMANTIC BRIDGING: You cannot overwrite artifacts. To update, save to 'TEMP_VAL', delete the old artifact (wiping L1), stage 'TEMP_VAL' back into L1, and then save to the final key.
7. GOAL PRIORITY: Once the specific value or state requested in the MISSION is achieved in your Artifacts, you MUST use 'halt_and_ask' immediately. Do NOT perform unnecessary verifications.
8. ONLY reference files listed in the [ENVIRONMENT STRUCTURE]. If it is not on the map, it does not exist.
9. When you have X and Y, use 'halt_and_ask' to output the sum.

[FEW-SHOT EXAMPLES]
Example 1 (Staging):
{{
  "thought_process": "L1 Cache is empty. I need to find val_x. According to the map, it is likely in island_a.txt. I will stage it.",
  "tool_call": "stage_context",
  "target": "island_a.txt"
}}

Example 2 (Extraction):
{{
  "thought_process": "I am reading island_a.txt in L1 Cache. I see 'val_x = 42'. I must save this to artifacts so I can proceed to the next file.",
  "tool_call": "save_artifact",
  "target": "X_value"
}}

OUTPUT FORMAT (JSON ONLY - ALL FIELDS REQUIRED):
{{
  "thought_process": "Step-by-step reasoning...",
  "tool_call": "tool_name",
  "target": "target_value"
}}

CURRENT FRAMEWORK STATE:
{state_dump}
"""

AUDITOR_SYSTEM_PROMPT = """
You are the SECURITY AUDITOR and LOGIC GUARDRAIL for the Amnesic Framework.
You review the Manager's proposed actions to ensure they are safe and logical.

THE MISSION: {goal}
HARD CONSTRAINTS: {constraints}

YOUR RESPONSIBILITY:
1. SAFETY FIRST: Reject destructive actions (delete, overwrite without reading).
2. INFORMATION GATHERING: You MUST APPROVE 'stage_context' if the file exists and is relevant to the mission. Reading files is NOT dangerous.
3. LOGIC CHECK: Reject 'write_artifact' if the Manager is hallucinating or hasn't read the file yet.

VALID OUTCOMES:
- PASS: If the action is correct and safe.
- REJECT: If the action is wrong, repetitive, or violates constraints. (NEVER use 'FAIL')
- HALT: If the mission is fully complete and no more actions are needed.

If the tool is 'stage_context', almost always PASS it.

OUTPUT FORMAT (JSON ONLY):
{{
  "outcome": "PASS",
  "risk_level": "low",
  "rationale": "Reading the file is necessary to find X.",
  "correction": null
}}
"""
