"""
Control Proof: 'Comparator' (Dual-Slot Failure)
Demonstrates the risk of standard agents handling 'Diff' tasks:
Loading two files simultaneously floods the context window, causing drift or OOM.
"""
import sys
import os
from rich.console import Console
from rich.panel import Panel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.control_proofs.control_lib import StandardReActAgent

console = Console()

def run_control_comparator():
    console.print(Panel(
        "[bold white]SCENARIO: Control Group (Standard Diff)[/bold white]\n"
        "[dim]Standard Agent attempts to compare two files.[/dim]\n"
        "[dim]It must load both into the SAME context window.[/dim]\n\n"
        "1. [red]Inputs[/red]: 'v1.py' and 'v2.py' (Large files).\n"
        "2. [yellow]Process[/yellow]: Read v1. Read v2. Compare.\n"
        "3. [red]Risk[/red]: Context Saturation / OOM.",
        title="Control Proof: Comparator Failure", border_style="red"
    ))

    # 1. Setup Files (Large enough to matter)
    content_a = "def func_a():\n    pass\n" * 50 # ~1000 chars -> 250 tokens
    content_b = "def func_b():\n    pass\n" * 50 # ~1000 chars -> 250 tokens
    
    with open("v1.py", "w") as f: f.write(content_a)
    with open("v2.py", "w") as f: f.write(content_b)
    
    mission = (
        "MISSION: Compare 'v1.py' and 'v2.py'. "
        "List the differences. "
        "Then call 'answer'."
    )
    
    # Restrictive limit to force the issue
    agent = StandardReActAgent(mission, token_limit=800)
    
    # 2. Execution
    console.print(Panel("Execution Trace", style="bold red"))
    
    status = "UNKNOWN"
    
    for i in range(10):
        step = agent.step()
        
        usage_bar = "█" * (step['context_len'] // 50)
        console.print(f"[Turn {step['turn']}] {step['action']} | Usage: {step['context_len']}/{step['limit']} {usage_bar}")
        
        if step['window_status'] != "OK":
            console.print(f"[bold red]WINDOW ALERT: {step['window_status']}[/bold red]")
            status = "FAILED"
        
        if step['action'] == "answer":
            console.print("[bold green]Mission Complete.[/bold green]")
            if status != "FAILED": status = "SUCCESS"
            break
            
    # 3. Audit
    console.print(Panel("[bold]Context Audit[/bold]", style="yellow"))
    if status == "FAILED" or step['context_len'] > 600:
        console.print("[bold red]✖ WARN: High Context Pressure[/bold red]")
        console.print("   Standard Agent permanently holds both files in history.")
        console.print("   Subsequent tasks would fail due to lack of space.")
    else:
        console.print("[bold green]✔ PASS: Fits (Unexpected)[/bold green]")

    # Cleanup
    if os.path.exists("v1.py"): os.remove("v1.py")
    if os.path.exists("v2.py"): os.remove("v2.py")

if __name__ == "__main__":
    run_control_comparator()
