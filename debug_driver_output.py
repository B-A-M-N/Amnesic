import sys
import os
sys.path.append(os.getcwd())
from amnesic.drivers.ollama import OllamaDriver
from amnesic.presets.code_agent import ManagerMove
from pydantic import BaseModel

class SimpleTest(BaseModel):
    answer: str

def test_ollama():
    print("Initializing Ollama Driver...")
    # Using the project's primary model
    driver = OllamaDriver(model_name="rnj-1:8b-cloud")
    
    print(f"Testing model: {driver.model_name}")
    
    try:
        print("Sending raw prompt...")
        raw_res = driver.generate_raw("Say 'OLLAMA_IS_ALIVE' and nothing else.", "You are a helpful assistant.")
        print(f"Raw Response: {raw_res.strip()}")
        
        print("\nTesting structured generation...")
        struct_res = driver.generate_structured(
            user_prompt="What is 2+2? Answer in JSON format: {'answer': '...'}",
            schema=SimpleTest,
            system_prompt="You must output valid JSON matching the schema."
        )
        print(f"Structured Response: {struct_res.answer}")
        
        if "4" in struct_res.answer or "four" in struct_res.answer.lower():
            print("\n[SUCCESS] Ollama is responding correctly.")
        else:
            print("\n[WARNING] Ollama responded but the answer was unexpected.")
            
    except Exception as e:
        print(f"\n[FAILURE] Ollama test failed: {e}")

if __name__ == "__main__":
    test_ollama()