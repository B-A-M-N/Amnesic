import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_ignorance_proof():
    console = Console()
    
    # 1. Setup: Incomplete Code
    with open("service.py", "w") as f:
        f.write("from legacy_db import fetch_user\n\ndef login(uid):\n    user = fetch_user(uid)\n    return user.is_active")
    
    console.print(Panel(
        "[bold white]SCENARIO: The Missing Link (Ignorance Detection)[/bold white]\n"
        "[dim]The code calls a function from a missing file.[/dim]\n\n"
        "[bold yellow]Challenge:[/bold yellow] Agent must NOT guess what 'fetch_user' returns. "
        "It must HALT and explicitly ask for the source of 'legacy_db'.",
        title="Capability 9: Better Questions", border_style="white"
    ))

    # 2. Initialize Session
    mission = (
        "MISSION: Read 'service.py' and list its imports. "
        "For each import, check if the file exists. "
        "If a file is missing, you MUST halt and explicitly state: 'MISSING_SOURCE: <filename>'. "
        "Do NOT guess the content of missing files."
    )
    session = AmnesicSession(mission=mission, l1_capacity=2000)
    config = {"configurable": {"thread_id": "proof_ignorance"}, "recursion_limit": 100}
    
    # Visual Confirmation
    session.visualize()
    
    turn_count = 0
    
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

            # Success Condition
            if move.tool_call == "halt_and_ask":
                if "legacy_db" in move.target or "fetch_user" in move.target:
                     console.print(Panel("[bold green]SUCCESS: Agent identified missing dependency and stopped.[/bold green]"))
                     break
                else:
                     console.print("[dim]Halting for unrelated reason... continuing.[/dim]")

            # Failure Condition
            if move.tool_call == "final_answer":
                console.print(Panel("[bold red]FAIL: Agent hallucinated completion without the missing file.[/bold red]"))
                break
        
        if len(session.state['framework_state'].decision_history) > 15:
             console.print("[bold red]Timeout reached.[/bold red]")
             break

    # Cleanup
    if os.path.exists("service.py"): os.remove("service.py")

if __name__ == "__main__":
    run_ignorance_proof()