"""
Master Demo: The Amnesic Lifecycle
This script demonstrates the full cognitive loop:
1. Mapping a repository (AST)
2. Staging a file into L1 (Volatile Context)
3. Extracting an authoritative Artifact into L2 (Backpack)
4. Performing a surgical code edit (Physical I/O)
5. Verifying the result.
"""
import os
import sys
from rich.console import Console
from rich.panel import Panel

# Ensure we can import the amnesic package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from amnesic import AmnesicSession

def run_demo():
    console = Console()
    
    # 1. Setup a dummy environment
    with open("service.py", "w") as f:
        f.write("def login(user):\n    return 'Success'")
    
    mission = (
        "MISSION: 1. Read service.py. 2. Extract the function signature as a 'CONTRACT' artifact. "
        "3. Edit service.py to change return to a dict: {'status': True}. "
        "4. Save a 'TOTAL' artifact saying 'DEMO_COMPLETE' and halt."
    )
    
    console.print(Panel("[bold green]Amnesic Master Demo[/bold green]\n"
                        "Running end-to-end lifecycle..."))

    # 2. Initialize Session
    session = AmnesicSession(
        mission=mission,
        root_dir=".",
        l1_capacity=2000
    )

    # 3. Execute
    session.run()
    
    # 4. Cleanup
    if os.path.exists("service.py"): os.remove("service.py")
    console.print("\n[bold cyan]Demo Finished.[/bold cyan]")

if __name__ == "__main__":
    run_demo()

