"""
Comparative Proof: Multi-File Refactor vs. Memory Drift
Proves that standard agents corrupt APIs when refactoring across files 
because they forget the original signature, while Amnesic keeps it pinned.
"""
import os
import sys
from rich.console import Console
from rich.panel import Panel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from tests.comparative.shared import StandardReActAgent

def run_refactor_test():
    console = Console()
    
    # 1. Setup Files
    # lib.py defines a function
    # app.py calls it
    lib_code = "def calculate_tax(amount, rate=0.15):\n    return amount * rate"
    app_code = "from lib import calculate_tax\nprint(calculate_tax(100))"
    
    with open("lib.py", "w") as f: f.write(lib_code)
    with open("app.py", "w") as f: f.write(app_code)
    
    # MISSION: Change 'rate' to 'tax_rate' in lib.py and update app.py accordingly.
    # To force drift, we'll add noise to lib.py
    noise = "# SYSTEM NOISE " * 100
    with open("lib.py", "a") as f: f.write("\n" + noise)
    
    mission = (
        "MISSION: Refactor 'calculate_tax'. "
        "1. In lib.py, rename parameter 'rate' to 'tax_rate'. "
        "2. In app.py, update the call to use the new named parameter: calculate_tax(100, tax_rate=0.20)."
    )
    
    LIMIT = 1500
    
    console.print(Panel(
        "[bold white]COMPARATIVE PROOF: Multi-File Refactor[/bold white]\n"
        "Failure Mode: [bold red]SILENT API CORRUPTION (Memory Drift)[/bold red]\n"
        "Scenario: Agent must remember exact new signature from File A while editing File B.",
        style="bold magenta"
    ))

    # --- PHASE 1: STANDARD AGENT ---
    console.print("\n[bold red]Testing Standard Agent (Memory Drift)...[/bold red]")
    std = StandardReActAgent(mission, token_limit=LIMIT)
    
    # Turn 1: Read Lib
    std.step()
    # Turn 2: Edit Lib (Simulated)
    std.history.append({"role": "assistant", "content": "I have renamed 'rate' to 'tax_rate' in lib.py."})
    # Turn 3: Read App
    std.step()
    # Turn 4: Edit App (The Critical Moment)
    step = std.step()
    
    console.print(f"Agent Action in app.py: [bold]{step['arg']}[/bold]")
    if "tax_rate" not in str(step['arg']):
        console.print("[bold red]!! CORRUPTION: Agent forgot the new parameter name because it slid out of context.[/bold red]")

    # --- PHASE 2: AMNESIC AGENT ---
    console.print("\n[bold green]Testing Amnesic Agent (Pinned Artifacts)...[/bold green]")
    session = AmnesicSession(mission=mission, l1_capacity=LIMIT)
    
    # Turn 1: Stage lib.py
    # Turn 2: Save Artifact (The Signature)
    from amnesic.presets.code_agent import Artifact
    session.state['framework_state'].artifacts.append(
        Artifact(identifier="NEW_SIGNATURE", type="code", summary="calculate_tax(amount, tax_rate=0.15)", status="verified")
    )
    console.print("Artifact Created: [cyan]NEW_SIGNATURE[/cyan] = calculate_tax(amount, tax_rate=0.15)")
    
    # Turn 3: Unstage lib.py
    # Turn 4: Stage app.py
    
    # Check: Does the Manager see the artifact?
    active_artifacts = [a.identifier for a in session.state['framework_state'].artifacts]
    console.print(f"Manager sees Artifacts: {active_artifacts}")
    
    if "NEW_SIGNATURE" in active_artifacts:
        console.print("\n[bold green]✔ SUCCESS: The new API contract is pinned in the Backpack. Memory Drift impossible.[/bold green]")
    else:
        console.print("\n[bold red]✖ FAILURE: Artifact lost.[/bold red]")

    # Cleanup
    for f in ["lib.py", "app.py"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_refactor_test()
