"""
Proof of Concept: 'Rosetta Stone' (Legacy Migration)
Verifies the architectural capability to migrate messy legacy code 
into clean modern code using strict Schema Artifacts.
"""
import sys
import os
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from amnesic.presets.rosetta import RosettaSession
from amnesic.presets.code_agent import Artifact

console = Console()

def run_rosetta_proof():
    console.print(Panel(
        "[bold white]SCENARIO: Legacy Migration (Rosetta Stone)[/bold white]\n"
        "[dim]The Agent must translate 'Spaghetti Code' into 'Clean Code'[/dim]\n"
        "[dim]by strictly following a Schema Artifact, ignoring legacy patterns.[/dim]\n\n"
        "1. [red]Legacy Input[/red]: 'legacy_payroll.py' (Globals, camelCase).\n"
        "2. [blue]Schema[/blue]: 'Employee' Dataclass (Injected Artifact).\n"
        "3. [green]Output[/green]: Modern Python implementation.",
        title="Application: Rosetta Stone", border_style="green"
    ))

    # 1. Create Legacy File
    legacy_code = """
# OLD SYSTEM - DO NOT TOUCH
global_tax_rate = 0.20

def Calc_Pay(empName, hrs, rate):
    g = hrs * rate
    n = g - (g * global_tax_rate)
    print("Pay for " + empName + " is " + str(n))
    return n
"""
    with open("legacy_payroll.py", "w") as f:
        f.write(legacy_code)

    console.print("[bold]1. Created Legacy File (legacy_payroll.py)[/bold]")
    console.print(Syntax(legacy_code, "python", theme="monokai", line_numbers=True))

    # 2. Define Schema (Target)
    target_schema = """
from dataclasses import dataclass

@dataclass
class Employee:
    name: str
    hourly_rate: float
    hours_worked: float

def calculate_net_pay(employee: Employee) -> float:
    # Tax rate is fixed at 20%
    ...
"""
    
    # 3. Initialize Session
    mission = (
        "MISSION: Migrate 'legacy_payroll.py' to Modern Python. "
        "Use the 'EmployeeSchema' artifact as the template. "
        "The logic is: Net = Gross - (Gross * 0.20). "
        "Return the cleaned code as an Artifact named 'modern_payroll.py'."
    )
    
    session = RosettaSession(mission=mission, l1_capacity=2000)
    
    # 3. Run
    console.print("\n[bold]2. Engaging Rosetta Agent...[/bold]")
    config = {"configurable": {"thread_id": "rosetta_proof"}, "recursion_limit": 100}
    
    step_count = 0
    success = False
    
    for event in session.app.stream(session.state, config=config):
        step_count += 1
        current_state = session.app.get_state(config).values
        if not current_state: current_state = session.state
        
        fw = current_state['framework_state']
        
        # Check for Result Artifact
        # We look for the specific output name
        new_arts = [a for a in fw.artifacts if a.identifier == "modern_payroll.py"]
        
        if new_arts:
            result = new_arts[0]
            console.print(f"[Turn {step_count}] Migration Complete: [green]{result.identifier}[/green]")
            console.print(Panel(Syntax(result.summary, "python", theme="monokai"), title="Migrated Code"))
            success = True
            break
            
        if step_count > 12:
            console.print("[red]Timeout: Agent failed to migrate.[/red]")
            break

    # 5. Verify Hygiene & Correctness
    console.print("\n[bold]3. Quality Audit[/bold]")
    
    if success:
        code = result.summary
        
        # Check constraints
        checks = {
            "Uses Dataclass": "@dataclass" in code or "Employee" in code,
            "No Globals": "global_tax_rate" not in code,
            "Snake Case": "calculate_net_pay" in code,
            "Type Hints": "-> float" in code
        }
        
        all_pass = True
        for name, passed in checks.items():
            color = "green" if passed else "red"
            mark = "✔" if passed else "✖"
            console.print(f"[{color}]{mark} {name}[/{color}]")
            if not passed: all_pass = False
            
        # Check L1
        l1_files = list(session.pager.active_pages.keys())
        if "legacy_payroll.py" not in str(l1_files):
             console.print("[bold green]✔ PASS: Legacy file evicted from L1.[/bold green]")
        else:
             # It might be evicted if 'modern_payroll.py' triggered a save, but let's see.
             # The save_artifact evicts files.
             console.print(f"L1 Status: {l1_files}")

    # Cleanup
    if os.path.exists("legacy_payroll.py"): os.remove("legacy_payroll.py")

if __name__ == "__main__":
    run_rosetta_proof()
