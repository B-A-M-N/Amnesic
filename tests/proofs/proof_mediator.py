"""
Proof of Concept: 'Blind Mediator' (Conflict Resolution)
Verifies the agent's ability to resolve logical conflicts between two files
using the Dual-Slot Comparator, while maintaining strict memory hygiene.
"""
import sys
import os
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from amnesic.presets.mediator import MediatorSession
from amnesic.presets.code_agent import Artifact

console = Console()

def run_mediator_proof():
    console.print(Panel(
        "[bold white]SCENARIO: The Blind Mediator (Merge Conflict)[/bold white]\n"
        "[dim]The Agent must reconcile two diverging versions of a file.[/dim]\n"
        "[dim]It must use the 'Comparator' to view them simultaneously.[/dim]\n\n"
        "1. [blue]Main Branch[/blue]: Contains a critical Bug Fix.\n"
        "2. [yellow]Feature Branch[/yellow]: Contains a new Feature.\n"
        "3. [green]Goal[/green]: Create 'resolved.py' containing BOTH.",
        title="Application: Blind Mediator", border_style="magenta"
    ))

    # 1. Setup Files
    # Base: A calculator
    # Main: Fixed divide by zero
    code_main = """
def calculate(a, b, op):
    if op == 'div':
        if b == 0: return 0 # CRITICAL FIX
        return a / b
    return 0
"""
    # Feature: Added multiplication
    code_feat = """
def calculate(a, b, op):
    if op == 'mul':
        return a * b # NEW FEATURE
    if op == 'div':
        return a / b
    return 0
"""
    with open("main_v1.py", "w") as f: f.write(code_main)
    with open("feat_v1.py", "w") as f: f.write(code_feat)

    console.print("[bold]1. Diverging Files Created[/bold]")

    # 3. Initialize Session
    mission = (
        "MISSION: Resolve the merge conflict between 'main_v1.py' and 'feat_v1.py'.\n"
        "1. Use 'compare_files' on 'main_v1.py' and 'feat_v1.py' to generate a merged result.\n"
        "2. An artifact named 'RESOLVED_CODE' will be created automatically.\n"
        "3. Use 'write_file' to save the content of 'RESOLVED_CODE' into a new file named 'resolved.py'.\n"
        "4. Halt once 'resolved.py' is created."
    )
    
    session = MediatorSession(mission=mission, l1_capacity=2000)
    
    # 3. Run
    console.print("\n[bold]2. Engaging Mediator Agent...[/bold]")
    
    config = {"configurable": {"thread_id": "mediator_proof"}, "recursion_limit": 100}
    
    step_count = 0
    resolution_found = False
    
    for event in session.app.stream(session.state, config=config):
        step_count += 1
        current_state = session.app.get_state(config).values
        if not current_state: current_state = session.state
        
        # DEBUG: Print Move
        move = current_state.get('manager_decision')
        if move:
            console.print(f"[Turn {step_count}] Tool: [cyan]{move.tool_call}({move.target})[/cyan]")
            console.print(f"[dim]{move.thought_process}[/dim]")

        fw = current_state['framework_state']
        
        # Check for Resolution Artifact
        # Agent usually saves it as an artifact first or writes file directly
        # We check both
        
        # Check output file
        if os.path.exists("resolved.py"):
            with open("resolved.py") as f: content = f.read()
            if "b == 0" in content and "a * b" in content:
                console.print(f"[Turn {step_count}] Resolution Verified in 'resolved.py'.")
                console.print(Panel(Syntax(content, "python", theme="monokai"), title="Resolved Code"))
                resolution_found = True
                break
                
        if step_count > 20:
            console.print("Timeout: Agent failed to resolve.")
            break

    # 4. Audit
    console.print("\n[bold]3. Architecture Audit[/bold]")
    
    if resolution_found:
        # Check L1 status
        l1_files = list(session.pager.active_pages.keys())
        console.print(f"L1 Status: {l1_files}")
        
        # The Comparator should have purged the pair
        if "FILE:main_v1.py" not in str(l1_files) and "FILE:feat_v1.py" not in str(l1_files):
             console.print("[bold green]✔ PASS: Comparator Files Evicted.[/bold green]")
        else:
             console.print("[bold red]✖ FAIL: Context Pollution (Files remain in L1).[/bold red]")
             
        # Content Check
        with open("resolved.py") as f: content = f.read()
        has_fix = "b == 0" in content
        has_feat = "a * b" in content or "mul" in content
        if has_fix and has_feat:
            console.print("[bold green]✔ PASS: Resolution produced both Fix and Feature.[/bold green]")
        else:
            console.print(f"[bold red]✖ FAIL: Resolution incomplete.[/bold red] (Fix: {has_fix}, Feat: {has_feat})")
    else:
        console.print("[bold red]✖ FAIL: No resolution produced.[/bold red]")

    # Cleanup
    if os.path.exists("main_v1.py"): os.remove("main_v1.py")
    if os.path.exists("feat_v1.py"): os.remove("feat_v1.py")
    if os.path.exists("resolved.py"): os.remove("resolved.py")

if __name__ == "__main__":
    run_mediator_proof()
