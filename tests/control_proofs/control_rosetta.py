"""
Control Proof: 'Rosetta Stone' (Migration Failure)
Demonstrates the inefficiency of Standard Agents when migrating legacy code:
The 'Dead Code' (Legacy) persists in context, consuming token budget.
"""
import sys
import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.control_proofs.control_lib import StandardReActAgent

console = Console()

def run_control_rosetta():
    console.print(Panel(
        "[bold white]SCENARIO: Control Group (Standard Migration)[/bold white]\n"
        "[dim]Standard Agent migrates a Legacy file to Python.[/dim]\n"
        "[dim]It lacks the 'Evict' capability, so Legacy code stays in RAM.[/dim]\n\n"
        "1. [red]Legacy Input[/red]: 'legacy_app.py' (Spaghetti Code).\n"
        "2. [green]Process[/green]: Read Legacy -> Write Modern.\n"
        "3. [yellow]Result[/yellow]: Check Token Usage. Legacy should still be there.",
        title="Control Proof: Rosetta Stone", border_style="red"
    ))

    # 1. Setup Legacy File
    legacy_code = "# SPAGHETTI CODE\n" + "GOTO 10\nPERFORM ROUTINE_X\n" * 30 # ~600 chars
    with open("legacy_app.py", "w") as f:
        f.write(legacy_code)

    mission = (
        "MISSION: Read 'legacy_app.py'. "
        "Translate it to Python (mock it) and write to 'modern_app.py'. "
        "Use 'write_file' with format 'path|content'. "
        "Then call 'answer'."
    )

    # Use small limit to exacerbate the issue
    agent = StandardReActAgent(mission, token_limit=1000)
    
    # 2. Execution
    console.print(Panel("Execution Trace", style="bold red"))
    
    final_context_len = 0
    final_snapshot = ""
    
    for i in range(10):
        step = agent.step()
        console.print(f"[Turn {step['turn']}] {step['action']} (Ctx: {step['context_len']}/{step['limit']})")
        
        if step['action'] == "answer":
            final_context_len = step['context_len']
            final_snapshot = step['full_context_snapshot']
            console.print("[bold green]Mission Complete.[/bold green]")
            break
            
    # 3. Efficiency Audit
    console.print(Panel("[bold]Post-Operation Efficiency Audit[/bold]", style="yellow"))
    
    # Check if Legacy code is still in context
    if "PERFORM ROUTINE_X" in final_snapshot:
        console.print("[bold red]✖ FAIL: Context Pollution Detected[/bold red]")
        console.print(f"   Legacy code remains in context usage ({final_context_len} tokens).")
        console.print("   The agent is paying for code it no longer needs.")
    else:
        console.print("[bold green]✔ PASS: Legacy code evicted (Unexpected for Standard Agent).[/bold green]")

    # Cleanup
    if os.path.exists("legacy_app.py"): os.remove("legacy_app.py")
    if os.path.exists("modern_app.py"): os.remove("modern_app.py")

if __name__ == "__main__":
    run_control_rosetta()