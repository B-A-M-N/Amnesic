from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class AuditProfile:
    """
    Configuration for the Amnesic Auditor's strictness.
    Controls the trade-off between Latency (Tokens) and Safety (Verification).
    """
    name: str
    
    # Actions that can skip the expensive LLM Audit layer if heuristics pass.
    # e.g., ["stage_context", "verify_step"]
    fast_path_actions: List[str] = field(default_factory=list)
    
    # Minimum embedding relevance (0.0 - 1.0) required to authorize a Fast Path.
    # If the action is "irrelevant" to the goal, it will still be rejected or sent to LLM.
    relevance_threshold: float = 0.6
    
    # Actions that MUST ALWAYS be audited by the LLM, regardless of heuristics.
    # e.g., ["write_file", "save_artifact"]
    strict_actions: List[str] = field(default_factory=list)
    
    # If True, allows slightly lower confidence scores to pass.
    allow_forgiveness: bool = False

# --- PRESETS ---

STRICT_AUDIT = AuditProfile(
    name="STRICT_AUDIT",
    fast_path_actions=[], # Nothing skips the judge
    relevance_threshold=0.0, # Irrelevant because everything goes to judge
    strict_actions=["*"], # Wildcard implies everything
    allow_forgiveness=False
)

FLUID_READ = AuditProfile(
    name="FLUID_READ",
    fast_path_actions=["stage_context", "unstage_context", "verify_step", "calculate"],
    relevance_threshold=0.55, # Moderate relevance required
    strict_actions=["write_file", "save_artifact", "edit_file", "halt_and_ask"],
    allow_forgiveness=True
)

HIGH_SPEED = AuditProfile(
    name="HIGH_SPEED",
    fast_path_actions=["stage_context", "unstage_context", "verify_step", "calculate", "save_artifact"],
    relevance_threshold=0.45, # Low relevance allowed
    strict_actions=["write_file", "edit_file"], # Only dangerous filesystem changes are strict
    allow_forgiveness=True
)

PROFILE_MAP: Dict[str, AuditProfile] = {
    "STRICT_AUDIT": STRICT_AUDIT,
    "FLUID_READ": FLUID_READ,
    "HIGH_SPEED": HIGH_SPEED
}