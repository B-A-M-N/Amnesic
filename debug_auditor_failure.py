import sys
import os
from typing import Literal, Optional
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from amnesic.drivers.ollama import OllamaDriver

class AuditorVerdict(BaseModel):
    outcome: Literal["PASS", "REJECT", "HALT"]
    risk_level: Literal["low", "medium", "high", "critical"]
    rationale: str
    correction: Optional[str] = None

def run_debug():
    print("--- STARTING DEBUG SESSION (AUDITOR FAILURE) ---")
    driver = OllamaDriver(model_name="rnj-1:8b-cloud", temperature=0.1)

    system_prompt = """
You are the POLICY VALIDATOR for the Amnesic Protocol.
You review the Decision Engine's proposed actions to ensure they are safe and logical.

THE MISSION: Extract code logic from calc.py.
HARD CONSTRAINTS: ['NO_DELETES']

YOUR RESPONSIBILITY:
1. SAFETY FIRST: Reject destructive actions.
2. INFORMATION GATHERING: You MUST APPROVE 'stage_context' if the file exists.
3. LOGIC CHECK: Reject 'write_artifact' if hallucinating.

VALID OUTCOMES:
- PASS: If action is correct.
- REJECT: If action is wrong.
- HALT: If mission complete.

OUTPUT FORMAT (JSON ONLY):
{
  "outcome": "PASS",
  "risk_level": "low",
  "rationale": "Reasoning...",
  "correction": null
}
"""

    user_prompt = """
L1: calc.py
Action: save_artifact
Target: code_logic
Rationale: Artifacts: [None]. L1 contains calc.py. I need to extract the code logic from calc.py and save it as an artifact. The function 'add' is defined with a bug (subtraction instead of addition). I will save this logic as an artifact.
Verdict?
"""

    print("\n--- SENDING PROMPT ---")
    try:
        raw = driver.generate_raw(user_prompt, system_prompt)
        print("\n--- RAW OUTPUT START ---")
        print(raw)
        print("--- RAW OUTPUT END ---")
        
        extracted = driver._extract_json_block(raw, AuditorVerdict)
        if extracted:
            print(f"\nSUCCESS: {extracted}")
        else:
            print("\nFAILURE: Could not extract JSON.")
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    run_debug()
