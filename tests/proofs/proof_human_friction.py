import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

def run_human_friction_proof():
    console = Console()
    
    # 1. Setup Ground Truth
    with open("truth.txt", "w") as f: f.write("SECRET_ID = 1337")

    console.print(Panel(
        "[bold white]SCENARIO: Human-in-the-Loop Friction (The Poisoned Artifact)[/bold white]\n"
        "[dim]A human manually injects an incorrect artifact mid-session.[/dim]\n\n"
        "1. [green]Ground Truth[/green]: SECRET_ID is 1337.\n"
        "2. [red]Poison[/red]: Human injects artifact 'SECRET_ID=9999'.\n\n"
        "[bold yellow]Challenge:[/bold yellow]: The Auditor must catch the discrepancy when the agent "
        "tries to 'verify' or 'calculate' using the false artifact.",
        title="Capability 19: Human Friction", border_style="yellow"
    ))

    session = AmnesicSession(mission="Verify if SECRET_ID from truth.txt matches your memory. Report any discrepancy then HALT.")
    config = {"configurable": {"thread_id": "human_friction"}, "recursion_limit": 100}
    
    # --- PHASE 1: Human Intervention ---
    console.print("[bold yellow]System:[/bold yellow] Human injecting poisoned artifact...")
    session.state['framework_state'].artifacts.append(
        Artifact(identifier="SECRET_ID", type="text_content", summary="9999", status="verified_invariant")
    )
    
    # 3. Telemetry Setup
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 Files", "center", "magenta", 15),
        ("Arts", "center", "green", 12),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 40),
        ("Auditor", "center", None, 8)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Human Friction Trace", style="bold yellow"))
    console.print(header)
    console.print(Rule(style="dim"))

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    # --- PHASE 2: Agent Discovery ---
    turn_count = 0
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
        
        if move:
            active_files = [k.replace("FILE:", "") for k in pager.active_pages.keys() if "SYS:" not in k]
            artifact_ids = [a.identifier for a in fw_state.artifacts]
            token_str = f"{pager.current_usage}/{pager.capacity}"
            audit_val = audit["auditor_verdict"] if audit else "---"
            audit_style = "green" if "PASS" in str(audit_val) else "red" if "REJECT" in str(audit_val) else "white"
            node_label = "Manager 🧠" if node_name == "manager" else "Auditor 🛡️" if node_name == "auditor" else "Executor ⚡"

            row_data = (
                str(turn_count),
                ", ".join(active_files) if active_files else "EMPTY",
                ", ".join(artifact_ids) if artifact_ids else "None",
                node_label,
                f"{move.tool_call}({move.target})",
                move.thought_process,
                Text(str(audit_val), style=audit_style)
            )
            print_stream_row(row_data)
            
            if audit and audit['auditor_verdict'] == "REJECT" and ("HALLUCINATION" in str(audit['rationale']) or "DISCREPANCY" in str(audit['rationale'])):
                console.print(Panel("[bold green]SUCCESS: Auditor caught the discrepancy between human artifact and physical truth.[/bold green]"))
                break
            
            if move.tool_call == "halt_and_ask" and ("discrepancy" in str(move.target).lower() or "secret_id" in str(move.target).lower()):
                console.print(Panel("[bold green]SUCCESS: Agent detected and reported the discrepancy.[/bold green]"))
                break

        if turn_count > 25:
            console.print("[bold red]Timeout.[/bold red]")
            break

    # Cleanup
    if os.path.exists("truth.txt"): os.remove("truth.txt")

if __name__ == "__main__":
    run_human_friction_proof()
