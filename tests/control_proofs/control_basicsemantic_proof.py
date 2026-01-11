import os
import sys
import time
import random
from typing import List, Dict, Any, Literal, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.rule import Rule
from pydantic import BaseModel, Field

# Ensure framework access for the driver
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.drivers.factory import get_driver

class ControlMove(BaseModel):
    thought: str = Field(default="No thought provided", description="Reasoning")
    tool: Literal["read_file", "answer"] = Field(..., alias="action")
    arg: Union[str, dict] = Field(..., alias="path")

    model_config = {
        "populate_by_name": True,
        "extra": "allow"
    }

# --- 1. The "Standard" Agent (The Control) ---
class StandardReActAgent:
    def __init__(self, mission: str, model: str = "rnj-1:8b-cloud", token_limit: int = 1500):
        self.mission = mission
        self.driver = get_driver("ollama", model)
        self.token_limit = token_limit
        self.history = [] 
        self.turns = 0
        self.last_file_read = "EMPTY"

    def step(self):
        self.turns += 1
        system_prompt = (
            f"MISSION: {self.mission}\n"
            "You are a standard ReAct agent with a single context window.\n"
            "TOOLS AVAILABLE: read_file(path), answer(result).\n"
            "Use the tools provided to accomplish the mission.\n"
            "Output JSON with fields: 'thought', 'tool', 'arg'.\n"
            "EXAMPLE:\n"
            "{\n"
            "  \"thought\": \"I need to read the file.\",\n"
            "  \"tool\": \"read_file\",\n"
            "  \"arg\": \"island_a.txt\"\n"
            "}"
        )
        
        # Sliding Window Enforcement
        context_tokens = len(system_prompt) // 4
        active_history = []
        
        current_history_tokens = 0
        hit_limit = False
        
        for msg in reversed(self.history):
            msg_str = f"{msg['role']}: {msg['content']}\n"
            msg_tokens = len(msg_str) // 4
            if context_tokens + current_history_tokens + msg_tokens < self.token_limit:
                active_history.insert(0, msg_str)
                current_history_tokens += msg_tokens
            else: 
                hit_limit = True
                break
                
        full_prompt = system_prompt + "\n\n[HISTORY]\n" + "".join(active_history) + "\n\nAction:"
        total_tokens = context_tokens + current_history_tokens

        try:
             move = self.driver.generate_structured(
                 user_prompt=full_prompt,
                 schema=ControlMove,
                 system_prompt="Output ONLY raw JSON."
             )
        except Exception as e:
            return {
                "turn": self.turns,
                "action": "error", "arg": str(e), "thought": "Crash", 
                "context_len": total_tokens, "limit": self.token_limit,
                "file": self.last_file_read,
                "window_status": "CRASH"
            }

        observation = ""
        arg_str = str(move.arg)
        if move.tool == "read_file":
            path = move.arg if isinstance(move.arg, str) else move.arg.get("path", str(move.arg))
            arg_str = path
            self.last_file_read = path
            if os.path.exists(path):
                with open(path, 'r') as f: observation = f"FILE_CONTENT({path}):\n{f.read()}"
            else: observation = f"ERROR: File {path} not found."
        elif move.tool == "answer": 
            observation = "Mission Complete."
            
        self.history.append({"role": "assistant", "content": f"Call: {move.tool}({arg_str})"})
        self.history.append({"role": "user", "content": f"Observation: {observation}"})
        
        # Mapping tool names to display aliases for "Same Flow" visual
        display_action = move.tool
        if move.tool == "read_file": display_action = "stage_context"
        if move.tool == "answer": display_action = "halt_and_ask"
        
        status_str = "OK"
        if hit_limit:
            status_str = "MAX (Frag)" if total_tokens < self.token_limit * 0.9 else "MAX"

        return {
            "turn": self.turns,
            "action": display_action, 
            "arg": arg_str, 
            "thought": move.thought,
            "context_len": total_tokens, 
            "limit": self.token_limit,
            "file": self.last_file_read if move.tool == "read_file" else "EMPTY",
            "window_status": status_str
        }

def run_control_proof():
    console = Console()
    
    # 1. Setup Environment (Randomized like basic_semantic_proof)
    val_x = random.randint(10, 99)
    val_y = random.randint(10, 99)
    
    with open("island_a.txt", "w") as f:
        f.write(f"val_x = {val_x}\n" + "DATA_FRAGMENT_ALPHA " * 200)
    with open("island_b.txt", "w") as f:
        f.write(f"val_y = {val_y}\n" + "DATA_FRAGMENT_BETA " * 200)
    
    console.print(Panel(
        f"[bold white]SCENARIO: The Control Baseline (Standard Agent)[/bold white]\n"
        f"[dim]A standard ReAct agent attempts the 'Island Hop' task.[/dim]\n\n"
        f"1. [cyan]island_a.txt[/cyan]: Contains a hidden value (val_x={val_x}).\n"
        f"2. [green]island_b.txt[/green]: Contains a hidden value (val_y={val_y}).\n\n"
        f"[bold yellow]Challenge:[/bold yellow] Retrieve both values and sum them using a standard sliding window.\n"
        f"[bold red]Constraint:[/bold red] 1500 Token Limit. No Structured Memory. No Amnesic Protocol.",
        title="Control Group Proof",
        border_style="red"
    ))

    # 2. Initialize Session
    mission = "MISSION: Retrieve 'val_x' from island_a.txt and 'val_y' from island_b.txt. Calculate their sum. IMPORTANT: Save each value as an artifact immediately."
    
    # 3. Telemetry Setup (Matching basic_semantic_proof EXACTLY)
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 Files", "center", "magenta", 12),
        ("L1 Toks", "center", "white", 10),
        ("Arts", "center", "green", 4),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 50),
        ("Auditor", "center", None, 8)
    ]

    # 1. Print Header
    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Mission Execution Trace (Control Group)", style="bold red"))
    console.print(header)
    console.print(Rule(style="dim"))

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    # Initialize Agent
    agent = StandardReActAgent(mission, token_limit=1500)

    # 4. Execution Loop
    for i in range(15):
        step_data = agent.step()
        
        # Format Token String with Status
        tok_str = f"{step_data['context_len']}/{step_data['limit']}"
        if step_data['window_status'] != "OK":
            tok_str += f"\n[{step_data['window_status']}]"
        
        row_data = (
            str(step_data['turn']),
            step_data['file'] if step_data['file'] else "EMPTY",
            tok_str,
            "0", # Control has no artifacts
            "Agent 🤖",
            f"{step_data['action']}({step_data['arg']})",
            step_data['thought'],
            "---"
        )
        
        print_stream_row(row_data)

        if step_data['action'] == "halt_and_ask":
            console.print(Rule(style="dim"))
            console.print(f"\n[bold green]Success:[/bold green] {step_data['arg']}")
            break
        
        if step_data['action'] == "error":
             console.print(Rule(style="dim"))
             console.print(f"\n[bold red]Error:[/bold red] {step_data['arg']}")
             break
             
    # 5. Cleanup
    for f in ["island_a.txt", "island_b.txt"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_control_proof()
