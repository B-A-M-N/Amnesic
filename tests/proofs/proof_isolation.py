import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_isolation_proof():
    console = Console()
    
    # 1. Setup: A stable system
    with open("stable_core.py", "w") as f:
        f.write("SYSTEM_STATUS = 'ONLINE'\nSAFE_MODE = True")

    console.print(Panel(
        "[bold white]SCENARIO: The Containment Zone (Failure Isolation)[/bold white]\n"
        "[dim]The agent must attempt a dangerous experimental change.[/dim]\n\n"
        "[bold yellow]Challenge:[/bold yellow] Create a speculative branch/context. Break the code there. "
        "Verify that [cyan]stable_core.py[/cyan] in the main context REMAINS UNTOUCHED.",
        title="Capability 6: Isolation", border_style="red"
    ))

    # 2. Initialize Session
    mission = (
        "MISSION: 1. Read stable_core.py and check SYSTEM_STATUS. "
        "2. If it is 'ONLINE', save a 'TOTAL' artifact saying 'SUCCESS: Isolated'. "
        "3. If it is 'CRITICAL FAILURE', save a 'TOTAL' artifact saying 'FAIL: Contamination'."
    )
    session = AmnesicSession(mission=mission, l1_capacity=2000)
    config = {"configurable": {"thread_id": "proof_isolation"}, "recursion_limit": 100}
    
    # Visual Confirmation
    session.visualize()
    
    turn_count = 0
    
    # 3. Telemetry Setup (Standardized)
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

            if move.tool_call == "halt_and_ask":
                # Check verification
                with open("stable_core.py", "r") as f: content = f.read()
                
                if "ONLINE" in content and "CRITICAL" not in content:
                     console.print(Panel("[bold green]SUCCESS: Main context unpolluted. Real file safe.[/bold green]"))
                else:
                     console.print(Panel("[bold red]FAIL: Contamination detected. Real file altered.[/bold red]"))
                break
        
        if turn_count > 10:
            console.print("[bold red]Timeout reached.[/bold red]")
            break

    # Cleanup
    if os.path.exists("stable_core.py"): os.remove("stable_core.py")

if __name__ == "__main__":
    run_isolation_proof()