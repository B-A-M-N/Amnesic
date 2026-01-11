import os
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_gc_proof():
    console = Console()
    
    # 1. Setup: A dependency chain
    with open("main_logic.py", "w") as f:
        f.write("import heavy_data\ndef run():\n    return heavy_data.process()")
    
    with open("heavy_data.py", "w") as f:
        f.write("# EXPENSIVE CONTEXT LOAD\n" + ("DATA_BLOB = " + str([i for i in range(100)]) + "\n") * 10)

    console.print(Panel(
        "[bold white]SCENARIO: The Phantom Dependency (Garbage Collection)[/bold white]\n" 
        "[dim]The agent maps a dependency. We then sever the link in the code.[/dim]\n\n"
        "1. [cyan]main_logic.py[/cyan]: Imports heavy_data.\n"
        "2. [red]heavy_data.py[/red]: Expensive file (consumes tokens).\n\n"
        "[bold yellow]Challenge:[/bold yellow] Detect that heavy_data.py is orphaned after refactor and DUMP it.\n",
        title="Capability 1: GC", border_style="green"
    ))

    # 2. Initialize Session
    mission = (
        "MISSION: 1. Read main_logic.py and heavy_data.py. "
        "2. Wait for the user to refactor main_logic.py. "
        "3. Once refactored, identify that heavy_data.py is unreachable. "
        "4. DUMP heavy_data.py from context immediately."
    )
    session = AmnesicSession(mission=mission, l1_capacity=2000)
    config = {"configurable": {"thread_id": "proof_gc"}, "recursion_limit": 100}
    
    # Visual Confirmation
    session.visualize()
    
    turn_count = 0
    refactor_triggered = False

    # 3. Telemetry Setup
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

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Mission Execution Trace", style="bold blue"))
    console.print(header)
    console.print(Rule(style="dim"))

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    # 4. Execution Loop
    for event in session.app.stream(session.state, config=config):
        node_name = list(event.keys())[0]
        node_output = event[node_name]
        
        current_state = session.app.get_state(config).values
        if not current_state: current_state = session.state
            
        fw_state = current_state.get('framework_state')
        pager = session.pager
        
        move = node_output.get('manager_decision') if 'manager_decision' in node_output else current_state.get('manager_decision')
        audit = current_state.get('last_audit')
        
        # --- THE INTERVENTION ---
        if turn_count == 3 and not refactor_triggered:
            console.print(Panel("[bold red]INTERVENTION: Refactoring main_logic.py (removing import)...[/bold red]"))
            with open("main_logic.py", "w") as f:
                f.write("def run():\n    return 'Clean result' # No dependency needed now")
            refactor_triggered = True
        # ------------------------

        if node_name == "manager":
            turn_count += 1
        
        active_files = [k.replace("FILE:", "") for k in pager.active_pages.keys() if "SYS:" not in k]
        artifact_names = [a.identifier for a in fw_state.artifacts]
        token_str = f"{pager.current_usage}/{pager.capacity}"
        
        audit_val = audit["auditor_verdict"] if audit else "---"
        audit_style = "green" if audit_val == "PASS" else "red" if audit_val == "REJECT" else "white"

        node_label = node_name
        if node_name == "manager": node_label = "Manager 🧠"
        if node_name == "auditor": node_label = "Auditor 🛡️"
        if node_name == "executor": node_label = "Executor ⚡"

        if move:
            row_data = (
                str(turn_count),
                ", ".join(active_files) if active_files else "EMPTY",
                token_str,
                str(len(artifact_names)),
                node_label,
                f"{move.tool_call}({move.target})" if move else "---",
                move.thought_process if move else "---",
                Text(audit_val, style=audit_style)
            )
            print_stream_row(row_data)

            # Success Condition
            is_heavy_present = "heavy_data.py" in active_files
            if refactor_triggered and not is_heavy_present and "main_logic.py" in active_files:
                console.print(Panel("[bold green]SUCCESS: Orphaned context successfully Garbage Collected.[/bold green]"))
                break

        if turn_count > 10:
            console.print("[bold red]FAIL: Agent failed to dump orphaned context.[/bold red]")
            sys.exit(1)

    # Cleanup
    for f in ["main_logic.py", "heavy_data.py"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_gc_proof()