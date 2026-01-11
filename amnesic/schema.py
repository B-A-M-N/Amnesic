from typing import Literal, Optional, List
from pydantic import BaseModel, Field

# --- THE SCHEMA (Constraint) ---
# This forces the 3B model to think in strict JSON, preventing hallucinations.
class NextMove(BaseModel):
    rationale: str = Field(..., description="Short reasoning for the decision.")
    tool_call: Literal["stage_context", "unstage_context", "save_artifact", "edit_file", "halt_and_ask", "verify_step"]
    target: str = Field(..., description="The filename, search query, or task ID.")
    update_hypothesis: Optional[str] = Field(None, description="New understanding of the situation (if changed).")
    new_unknowns: Optional[List[str]] = Field(None, description="New questions or missing info discovered.")
    confidence: float = Field(..., description="0.0 to 1.0")
