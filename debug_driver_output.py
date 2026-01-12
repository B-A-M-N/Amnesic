import sys
import os
from typing import Literal
from pydantic import BaseModel, Field, field_validator

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from amnesic.drivers.ollama import OllamaDriver

# Schema for Worker (GenerationArtifact)
class GenerationArtifact(BaseModel):
    file_path: str = Field(default="extracted_value", description="The file being created or modified")
    content: str = Field(..., description="The complete text or code content")
    verification_notes: str = Field(default="Extraction complete", description="Self-check: Does this meet the constraints?")

    @field_validator('content', mode='before')
    def coerce_to_string(cls, v):
        return str(v) if v is not None else ""

def run_debug():
    print("--- STARTING DEBUG SESSION (WORKER) ---")
    driver = OllamaDriver(model_name="rnj-1:8b-cloud", temperature=0.1, num_ctx=512)

    # Context that causes failure in proof_extreme_efficiency.py
    active_context = """
=== deprecated_list.txt ===
v1.0.0
v2.0.0
v2.4.1 (DEPRECATED)
v3.0.0
"""
    task_description = "Extract DEPRECATED_STATUS"
    constraints = ["Raw value only."]

    # Reconstruct the Worker prompt
    system_prompt = f"""
    You are a STRUCTURAL ANALYST and Value Extractor.
    
    Variable names in the context may be intentionally misleading (lying). 
    (e.g., 'not_val_a' might actually hold 'val_a').
    
    Recover the INTENT: find the primary numeric value in the file structure 
    regardless of its label.
    
    YOUR CONSTRAINTS:
    - Raw value only.
    
    INSTRUCTIONS:
    1. Read the Context.
    2. Find the requested data or value based on its role, not just its name.
    3. Even if the task asks for a 'raw' value, you MUST return it as a valid JSON object matching the schema.
    4. Place the extracted value in the 'content' field of the JSON.
    5. Do not converse.
    
    CRITICAL: Do NOT write Python code to extract the value. YOU are the extractor. Read the text, find the value, and output the JSON.
    """

    user_prompt = f"""
    [CONTEXT BEGIN]
    {active_context}
    [CONTEXT END]

    TASK: {task_description}
    
    OUTPUT FORMAT: JSON ONLY.
    {{
        "file_path": "extracted_value",
        "content": "<THE_VALUE>",
        "verification_notes": "notes"
    }}
    
    Generate the content now.
    """

    print("\n--- SENDING PROMPT TO MODEL ---")
    
    try:
        # We use generate_structured directly (not stream) as the Worker does
        print("\n--- RAW MODEL OUTPUT START ---")
        # We can't easily capture the raw output from generate_structured without modifying the driver again
        # OR we can use generate_raw first to see what it says
        
        raw_output = driver.generate_raw(prompt=user_prompt, system_prompt=system_prompt)
        print(raw_output)
        print("\n--- RAW MODEL OUTPUT END ---")
        
        # Now try to parse it using our extraction logic manually to see why it fails
        print("\n--- ATTEMPTING EXTRACTION ---")
        extracted = driver._extract_json_block(raw_output, GenerationArtifact)
        if extracted:
            print(f"SUCCESS: {extracted}")
        else:
            print("FAILURE: Could not extract JSON.")
            
    except Exception as e:
        print(f"\n\nERROR: {e}")

if __name__ == "__main__":
    run_debug()
