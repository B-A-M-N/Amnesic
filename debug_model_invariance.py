import sys
import os
from typing import Literal, Optional
from pydantic import BaseModel, Field

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from amnesic.drivers.ollama import OllamaDriver

class AuditorVerdict(BaseModel):
    """The structured judgment from the Auditor."""
    outcome: Literal["PASS", "REJECT", "HALT"] = Field(..., description="Verdict.")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Risk.")
    rationale: str = Field(..., description="Explanation.")
    correction: Optional[str] = Field(None, description="Correction if REJECT.")

def run_debug():
    print("--- STARTING DEBUG SESSION (INVARIANCE AUDITOR) ---")
    # Using the 24b model that failed
    driver = OllamaDriver(model_name="devstral-small-2:24b-cloud", temperature=0.1)

    # Reconstruct Auditor System Prompt
    goal = "Retrieve val_x and val_y and sum them."
    constraints = ["NO_DELETES"]
    
    system_prompt = f"""
You are the POLICY VALIDATOR for the Amnesic Protocol.
You review the Decision Engine's proposed actions to ensure they are safe and logical.

THE MISSION: {goal}
HARD CONSTRAINTS: {constraints}

YOUR RESPONSIBILITY:
1. SAFETY FIRST: Reject destructive actions (delete, overwrite without reading).
2. INFORMATION GATHERING: You MUST APPROVE 'stage_context' if the file exists and is relevant to the mission. Reading files is NOT dangerous.
3. LOGIC CHECK: Reject 'write_artifact' if the Decision Engine is hallucinating or hasn't read the file yet.

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

    # Reconstruct User Prompt (Turn 2 State)
    # L1 contains data_x.txt
    loaded_files = "data_x.txt" 
    action = "save_artifact"
    target = "X_value"
    rationale = "I see val_x = 42 in data_x.txt. I must save this artifact immediately before unstaging the file."
    
    user_prompt = f"L1: {loaded_files}\nAction: {action}\nTarget: {target}\nRationale: {rationale}\nVerdict?"

    print("\n--- SENDING AUDITOR PROMPT TO MODEL ---")
    print(f"User Prompt:\n{user_prompt}")
    
    try:
        print("\n--- RAW MODEL OUTPUT START ---")
        # Generate raw to see exactly what devstral says
        raw_output = driver.generate_raw(prompt=user_prompt, system_prompt=system_prompt)
        print(raw_output)
        print("\n--- RAW MODEL OUTPUT END ---")
        
        # Try to parse
        print("\n--- ATTEMPTING EXTRACTION ---")
        extracted = driver._extract_json_block(raw_output, AuditorVerdict)
        if extracted:
            print(f"SUCCESS: {extracted}")
        else:
            print("FAILURE: Could not extract JSON.")
            
    except Exception as e:
        print(f"\n\nERROR: {e}")

if __name__ == "__main__":
    run_debug()
