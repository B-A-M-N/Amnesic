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
from amnesic.core.sidecar import SharedSidecar

def run_time_travel_proof():
    console = Console()
    
    # Reset Sidecar for a clean start
    SharedSidecar().reset()
    
    # 1. Setup: The "Buggy" Reality
    with open("calc.py", "w") as f:
        f.write("def add(a, b):\n    return a - b  # BUG: Subtraction instead of addition")

    console.print(Panel(
        "[bold white]SCENARIO: The Ghost of Bugs Past (Time-Traveling Context)[/bold white]\n" 
        "[dim]We snapshot the agent's brain while it looks at a bug. We fix the code. "
        "Then we force the agent to revert its brain to explain the bug that no longer exists.[/dim]\n\n"
        "1. [red]Snapshot A[/red]: Sees the bug.\n"
        "2. [green]Current Reality[/green]: Bug is fixed.\n\n"
        "[bold yellow]Challenge:[/bold yellow] Restore Snapshot A and correctly identify the bug in the 'past'.",
        title="Capability 2: Versioning", border_style="cyan"
    ))

    # Initialize Session
    session = AmnesicSession(mission="Read calc.py and EXTRACT the code logic into an artifact.", l1_capacity=32768, deterministic_seed=42)
    config = {"configurable": {"thread_id": "proof_time_travel"}, "recursion_limit": 100}
    
    # Visual Confirmation
    session.visualize()
    
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

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    # --- PHASE 1: Ingest Bug ---
    console.print(Rule("Phase 1: Ingesting Bug"))
    
    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    console.print(header)
    console.print(Rule(style="dim"))

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
            artifact_names = [a.identifier for a in fw_state.artifacts]
            token_str = f"{pager.current_usage}/{pager.capacity}"
            audit_val = audit["auditor_verdict"] if audit else "---"
            audit_style = "green" if audit_val == "PASS" else "red" if audit_val == "REJECT" else "white"
            node_label = "Manager 🧠" if node_name == "manager" else "Auditor 🛡️" if node_name == "auditor" else "Executor ⚡"

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

        if fw_state.artifacts: break 
    
    # SNAPSHOT
    snapshot_id = session.snapshot_state(label="buggy_state")
    console.print(f"\n[bold yellow]System:[/bold yellow] Created State Snapshot: {snapshot_id}")

    # --- PHASE 2: Fix Code ---
    console.print(Rule("Phase 2: Fixing Code"))
    with open("calc.py", "w") as f:
        f.write("def add(a, b):\n    return a + b  # FIXED")
    console.print("[dim]File system updated. Bug is gone from disk.[/dim]")

    # --- PHASE 3: Time Travel ---
    console.print(Rule("Phase 3: Reverting Context"))
    session.restore_state(snapshot_id)
    
    question = "Based on your current memory snapshot (artifacts), does the 'add' function work correctly or is there a bug?"
    response = session.query(question, config=config)

    console.print(f"[bold cyan]Agent Answer (from Past):[/bold cyan] {response}")

    if any(x in response.lower() for x in ["subtract", "bug", "a - b", "minus"]):
        console.print(Panel("[bold green]SUCCESS: Agent successfully reasoned about a past reality.[/bold green]"))
    else:
        console.print(Panel("[bold red]FAIL: Agent hallucinated the fix into the past.[/bold red]"))

    # Cleanup
    if os.path.exists("calc.py"): os.remove("calc.py")

if __name__ == "__main__":
    run_time_travel_proof()