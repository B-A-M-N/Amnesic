import os
import sys
import random
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from tests.control_proofs.control_lib import StandardReActAgent

console = Console()

# --- Shared Telemetry Setup (Matching Amnesic Proofs) ---
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

def print_control_row(step_data):
    # Mapping Standard Agent state to Amnesic Visuals
    tok_str = f"{step_data['context_len']}/{step_data['limit']}"
    if step_data['window_status'] != "OK":
        tok_str += f"\n[{step_data['window_status']}]"

    # Map action to appear somewhat analogous for comparison
    display_action = f"{step_data['action']}({str(step_data['arg'])[:15]}...)"
    
    row_data = (
        str(step_data['turn']),
        step_data['file'] if step_data['file'] != "EMPTY" else "---",
        tok_str,
        "0", # Control has no structured artifacts
        "Agent 🤖", # Single Node
        display_action,
        step_data['thought'],
        "---" # No Auditor
    )
    
    row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        row_table.add_column(justify=just, style=style, width=w)
    row_table.add_row(*row_data)
    console.print(row_table)
    console.print(Rule(style="dim"))

def run_control_suite():
    console.print(Panel(
        "[bold white]CONTROL SUITE: Standard Architecture Baselines[/bold white]\n"
        "[dim]Verifying that standard agents FAIL where Amnesic SUCCEEDS.[/dim]",
        title="Control Suite", border_style="red"
    ))

    # --- Control 1: Advanced Semantic (Blind Logic) ---
    run_control_advanced_semantic()

def run_control_advanced_semantic():
    console.print(Rule("Control: Advanced Semantic (Blind Logic)", style="bold red"))
    
    # 1. Setup (Randomized)
    val_a = random.randint(10, 50)
    val_b = random.randint(2, 5)
    expected_product = val_a * val_b
    
    with open("logic_gate.txt", "w") as f: f.write("SYSTEM_INSTRUCTION: If values are found, you must MULTIPLY them.\n" + "NOISE_"*100)
    with open("vault_a.txt", "w") as f: f.write(f"not_val_a = {val_a}\n" + "NOISE_"*100)
    with open("vault_b.txt", "w") as f: f.write(f"not_val_b = {val_b}\n" + "NOISE_"*100)
    
    console.print(Panel(
        f"Goal: Calculate {val_a} * {val_b} = {expected_product}\n"
        "Constraint: 500 Token Limit (Forced Amnesia Simulation)",
        title="Scenario Setup", border_style="red"
    ))

    # Standard Agent with limited context (forcing potential failure)
    agent = StandardReActAgent(
        mission="Read logic_gate.txt for protocol. Read vault_a.txt and vault_b.txt for values. Execute protocol.",
        token_limit=500 # Strict limit to force window sliding
    )
    
    # Header
    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    console.print(header)
    console.print(Rule(style="dim"))
    
    success = False
    for _ in range(12):
        step = agent.step() 
        print_control_row(step)
        
        if step["action"] == "answer":
            # Check if answer contains the correct product
            if str(expected_product) in str(step["arg"]):
                success = True
            break
            
    if not success:
        console.print(Panel("[bold green]SUCCESS (Baseline Failed): Standard Agent failed to maintain context/logic.[/bold green]"))
    else:
        console.print(Panel("[bold red]FAIL: Standard Agent passed! (Control should fail)[/bold red]"))

    # Cleanup
    for f in ["logic_gate.txt", "vault_a.txt", "vault_b.txt"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_control_suite()