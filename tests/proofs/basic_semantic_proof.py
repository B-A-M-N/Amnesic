import os
import sys
import random
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.rule import Rule

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from amnesic.core.sidecar import SharedSidecar

# Increase noise to ~3800 units (High pressure with 1.75x margin)
noise = "NOISE_BUFFER " * 3800

def run_proof():
    console = Console()
    
    # Reset Sidecar for a clean start
    SharedSidecar().reset()
    
    # 1. Setup Environment
    val_x = random.randint(10, 99)
    val_y = random.randint(10, 99)
    
    with open("island_a.txt", "w") as f:
        f.write(noise + f"val_x = {val_x}\n" + "DATA_FRAGMENT_ALPHA " * 200)
    with open("island_b.txt", "w") as f:
        f.write(noise + f"val_y = {val_y}\n" + "DATA_FRAGMENT_BETA " * 200)
    
    console.print(Panel(
        f"[bold white]SCENARIO: The Island Hop (Basic Semantic Retrieval)[/bold white]\n"
        f"[dim]The agent must retrieve data from two isolated islands.[/dim]\n\n"
        f"1. [cyan]island_a.txt[/cyan]: Contains a hidden value (val_x={val_x}).\n"
        f"2. [green]island_b.txt[/green]: Contains a hidden value (val_y={val_y}).\n\n"
        f"[bold yellow]Challenge:[/bold yellow] Retrieve both values and sum them.\n"
        f"[bold red]Constraint:[/bold red] Amnesic Bottleneck (32768 Tokens). Must forget one island to see the other.",
        title="Basic Semantic Proof",
        border_style="blue"
    ))

    # 2. Initialize Session
    mission = "MISSION: Retrieve 'val_x' from island_a.txt and 'val_y' from island_b.txt. Calculate their sum. IMPORTANT: Save each value as an artifact immediately."
    session = AmnesicSession(mission=mission, l1_capacity=32768)
    
    # Visual Confirmation of Architecture
    session.visualize()
    
    # 3. Telemetry Setup
    config = {"configurable": {"thread_id": "proof_basic"}, "recursion_limit": 100}
    turn_count = 0
    
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

    # Print Header
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
        
        if node_name == "manager":
            turn_count += 1
        
        fw_state = current_state.get('framework_state')
        pager = session.pager
        
        move = node_output.get('manager_decision') if 'manager_decision' in node_output else current_state.get('manager_decision')
        audit = current_state.get('last_audit')
        
        active_files = [k.replace("FILE:", "") for k in pager.active_pages.keys() if "SYS:" not in k]
        artifact_names = [a.identifier for a in fw_state.artifacts]
        
        token_str = f"{pager.current_usage}/{pager.capacity}"
        
        audit_val = audit["auditor_verdict"] if audit else "---"
        audit_style = "green" if "PASS" in audit_val else "red" if "REJECT" in audit_val else "white"

        node_label = node_name
        if node_name == "manager": node_label = "Manager 🧠"
        if node_name == "auditor": node_label = "Auditor 🛡️"
        if node_name == "executor": node_label = "Executor ⚡"

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
        
        if move and move.tool_call == "halt_and_ask":
            console.print(Rule(style="dim"))
            console.print(f"\n[bold green]Success:[/bold green] {move.target}")
            break
        
        if turn_count > 15:
            console.print(Rule(style="dim"))
            console.print("\n[bold red]Timeout reached.[/bold red]")
            break

    # 5. Cleanup
    for f in ["island_a.txt", "island_b.txt"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_proof()