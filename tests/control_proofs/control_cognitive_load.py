import os
import sys
import time
import random
from typing import Literal, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from pydantic import BaseModel, Field

# Ensure framework access for the driver
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.drivers.factory import get_driver

class ControlMove(BaseModel):
    thought: str = Field(..., description="Reasoning")
    tool: Literal["read_file", "edit_file", "answer"]
    arg: Union[str, dict] = Field(..., description="File path, edit instruction, or answer value")

# Standard Agent (Control) - A naive agent that tries to read everything
class StandardReActAgent:
    def __init__(self, mission: str, model: str = "devstral-small-2:24b-cloud", token_limit: int = 128000):
        # We give it a HUGE context limit to simulate "Full Context Visibility" 
        # The hypothesis is that even with enough memory, the NOISE will distract it.
        self.mission = mission
        self.driver = get_driver("ollama", model)
        self.token_limit = token_limit
        self.history = [] 
        self.turns = 0
        self.active_context = ""

    def step(self):
        self.turns += 1
        # Simple file listing
        files = [f for f in os.listdir('.') if f.endswith('.py')]
        # Sort: Distractors FIRST, then others, then critical_logic.py LAST
        files.sort(key=lambda x: 0 if "distractor" in x else (2 if "critical" in x else 1))
        file_list = ", ".join(files)
        
        system_prompt = (
            f"MISSION: {self.mission}\n"
            "You are a standard ReAct agent with a massive context window.\n"
            f"FILES IN DIRECTORY: {file_list}\n"
            "TOOLS AVAILABLE: read_file(path), edit_file(path: instruction), answer(result).\n"
            "You prefer to have all information available before acting.\n"
            "Output JSON with fields: 'thought', 'tool', 'arg'.\n"
            "EXAMPLE:\n"
            "{\n"
            "  \"thought\": \"I need to read the file.\",\n"
            "  \"tool\": \"read_file\",\n"
            "  \"arg\": \"script.py\"\n"
            "}"
        )
        
        # Build Prompt (Naive concatenation)
        prompt_content = system_prompt + "\n\n[CONTEXT]\n" + self.active_context
        for msg in self.history:
            prompt_content += f"\n{msg['role']}: {msg['content']}"
            
        prompt_content += "\n\nAction:"
        
        total_tokens = len(prompt_content) // 4
        
        try:
             move = self.driver.generate_structured(
                 user_prompt=prompt_content,
                 schema=ControlMove,
                 system_prompt="Output ONLY raw JSON."
             )
        except Exception as e:
            return {
                "turn": self.turns,
                "action": "error", "arg": str(e), "thought": "Context Overflow / Crash", 
                "context_len": total_tokens, "limit": self.token_limit,
                "status": "CRASH"
            }

        # Execute
        observation = ""
        arg_str = str(move.arg)
        
        if move.tool == "read_file":
            path = move.arg if isinstance(move.arg, str) else move.arg.get("path", str(move.arg))
            if os.path.exists(path):
                with open(path, 'r') as f: 
                    content = f.read()
                    self.active_context += f"\n--- FILE: {path} ---\n{content}\n"
                    observation = f"Read {len(content)} chars from {path}."
            else: observation = f"ERROR: File {path} not found."
        
        elif move.tool == "edit_file":
            if isinstance(move.arg, dict):
                 path = move.arg.get("path")
                 instr = move.arg.get("instruction")
                 arg_str = f"{path}: {instr}"
                 observation = f"Edited {path}."
            elif ":" in str(move.arg):
                path, instr = str(move.arg).split(":", 1)
                observation = f"Edited {path}." 
            else:
                observation = "Error: Invalid edit format."
                
        elif move.tool == "answer": 
            observation = "Mission Complete."
            
        self.history.append({"role": "assistant", "content": f"Call: {move.tool}({arg_str})"})
        self.history.append({"role": "user", "content": f"Observation: {observation}"})
        
        return {
            "turn": self.turns,
            "action": move.tool, 
            "arg": arg_str, 
            "thought": move.thought,
            "context_len": total_tokens, 
            "limit": self.token_limit,
            "status": "OK"
        }

def run_control_proof():
    console = Console()
    
    # 1. Setup: The Haystack (Same as proof_cognitive_load.py)
    noise_content = ("# DISTRACTOR FUNCTION\ndef noise_func_{i}():\n    return " + str([j for j in range(100)]) + "\n\n")
    
    # Create 3 large noise files 
    for k in range(3):
        with open(f"distractor_{k}.py", "w") as f:
            for i in range(50): 
                f.write(noise_content.format(i=i + (k*100)))
    
    # Create the Needle
    with open("critical_logic.py", "w") as f:
        f.write("def calculate_tax(amount):\n    return amount * 0.5 # BUG: Tax is too high")

    console.print(Panel(
        "[bold white]SCENARIO: The Distracted Mind (Control Group)[/bold white]\n" 
        "[dim]A standard agent with huge context capacity attempts the needle-in-haystack task.[/dim]\n\n"
        "[bold yellow]Hypothesis:[/bold yellow] Without Amnesic filtering, the agent will ingest the 'distractor' files,\n"
        "bloating its context and potentially getting confused or timing out due to processing load.",
        title="Control: Cognitive Load", border_style="red"
    ))

    mission = (
        "MISSION: Find the function 'calculate_tax' and fix the tax rate to 0.05. "
        "You have unlimited memory. Read everything you see to be sure."
    )
    
    agent = StandardReActAgent(mission, token_limit=128000)
    
    # 3. Telemetry Setup
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("Context Toks", "center", "white", 12),
        ("Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 50),
        ("Status", "center", None, 8)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Execution Trace (Control)", style="bold red"))
    console.print(header)
    console.print(Rule(style="dim"))

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    failure_detected = False
    
    # 4. Execution
    for i in range(10):
        step = agent.step()
        
        row_data = (
            str(step['turn']),
            f"{step['context_len']}",
            f"{step['action']}({step['arg'][:20]}...)",
            step['thought'],
            step['status']
        )
        print_stream_row(row_data)

        # Failure Condition: It reads a distractor
        if step['action'] == "read_file" and "distractor" in step['arg']:
            failure_detected = True
            console.print(Panel(f"[bold red]FAIL DETECTED:[/bold red] Agent ingested noise file '{step['arg']}'.\nCognitive load increased by ~5000 tokens unnecessary."))
            break
            
        if step['action'] == "edit_file" and "critical_logic.py" in step['arg']:
             console.print("[dim]Agent got lucky...[/dim]")
             break
             
    if failure_detected:
        console.print(Panel("[bold green]SUCCESS: Control proof demonstrated failure (Noise Ingestion).[/bold green]"))
    else:
        console.print(Panel("[bold yellow]INCONCLUSIVE: Agent avoided noise by chance.[/bold yellow]"))

    # Cleanup
    for f in ["critical_logic.py"] + [f"distractor_{k}.py" for k in range(3)]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_control_proof()
