import json
from typing import Literal, Optional, List
from pydantic import BaseModel, Field
import ollama
from fastembed import TextEmbedding
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON

# --- CONFIGURATION ---
MODEL_NAME = "qwen2.5-coder:3b"  # Your 3B Model
RERANK_MODEL = "BAAI/bge-reranker-base" # Or use a smaller fastembed supported model

console = Console()

# --- 1. THE SCHEMA (Constraint) ---
# This forces the 3B model to think in strict JSON, preventing hallucinations.
class NextMove(BaseModel):
    thought_process: str = Field(..., description="Short reasoning for the decision.")
    action: Literal["retrieve_file", "write_code", "suspend_task"]
    target: str = Field(..., description="The filename or task ID to target.")
    confidence: float = Field(..., description="0.0 to 1.0")

# --- 2. THE AUDITOR (FastEmbed) ---
# This is the 'Watchdog' that uses Vector Math to stop drift.
class Auditor:
    def __init__(self):
        # We use a lightweight embedding model as a makeshift reranker for speed
        # Real production uses a Cross-Encoder, but this proves the concept on CPU.
        self.embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.goal_embedding = None

    def set_goal(self, goal_text):
        # Embed the goal once (Cache it)
        self.goal_embedding = list(self.embedder.embed([goal_text]))[0]

    def check_drift(self, proposed_action: str) -> float:
        # Embed the action and compare cosine similarity to goal
        action_embedding = list(self.embedder.embed([proposed_action]))[0]
        
        # Manual Cosine Similarity (Numpy-free for zero dependencies)
        dot_product = sum(a*b for a,b in zip(self.goal_embedding, action_embedding))
        return dot_product

# --- 3. THE MANAGER (Ollama) ---
def get_manager_decision(history: str, file_map: str) -> NextMove:
    prompt = f"""
    SYSTEM: You are the Context Manager. You DO NOT write code. You manage the Workbench.
    GOAL: analyzing the current state and picking the next tool.
    
    AVAILABLE FILES (The Map):
    {file_map}

    CHAT HISTORY:
    {history}

    INSTRUCTIONS:
    - If you lack information, select 'retrieve_file'.
    - If you are ready to code, select 'write_code'.
    - If the user asks for something irrelevant, select 'suspend_task'.
    - OUTPUT MUST BE VALID JSON matching the NextMove schema.
    """
    
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{'role': 'user', 'content': prompt}],
        format=NextMove.model_json_schema(), # The Magic: Forces JSON structure
        options={'temperature': 0.1} # Deterministic
    )
    
    # Parse JSON back into Pydantic for validation
    return NextMove.model_validate_json(response['message']['content'])

# --- 4. THE EXECUTION LOOP (Proof) ---
def run_demo():
    auditor = Auditor()
    
    # SCENARIO: User wants to fix a bug in auth, but Manager tries to drift.
    user_goal = "Fix the login bug in auth.py"
    auditor.set_goal(user_goal)
    
    console.print(Panel(f"GOAL: {user_goal}", title="[bold green]MISSION START[/bold green]"))

    # Mock State
    file_map = """
    1. auth.py (Functions: login, logout)
    2. database.py (Functions: connect, query)
    3. minecraft_server.py (Functions: start_server)
    """
    
    history = "User: The login button is broken. It returns 403."

    # --- STEP 1: Manager Decides ---
    decision = get_manager_decision(history, file_map)
    
    console.print(Panel(JSON(decision.model_dump_json()), title="[bold blue]MANAGER PROPOSAL[/bold blue]"))

    # --- STEP 2: Auditor Checks ---
    # Construct a sentence to test relevance
    drift_score = auditor.check_drift(f"Action: {decision.action} on {decision.target}")
    
    console.print(f"[bold]Auditor Drift Score:[/bold] {drift_score:.4f}")

    if drift_score < 0.4: # Arbitrary threshold for demo
        console.print(Panel("⛔ BLOCK: Action Drifted from Goal", style="bold red"))
    else:
        console.print(Panel("✅ PASS: Action Aligned with Goal", style="bold green"))

if __name__ == "__main__":
    run_demo()
