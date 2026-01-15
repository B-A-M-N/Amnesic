import os
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.syntax import Syntax

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

noise = "NOISE_BUFFER " * 1200

def run_code_basic_proof():
    console = Console()
    
    # 1. Setup: A buggy application
    source_code = "def calculate_tax(price):\n    return price * 0.5  # BUG: Tax is 50%, should be 5%"
    with open("app.py", "w") as f:
        f.write(source_code)

    mission = (
        "MISSION: 1. Read app.py. "
        "2. Identify the bug (tax rate is too high). "
        "3. Use 'edit_file' to change 0.5 to 0.05. "
        "4. Verify the fix."
    )
    session = AmnesicSession(mission=mission, l1_capacity=3000)
    
    # Visual Confirmation of Architecture (Boot Sequence)
    session.visualize()

    console.print(Panel(
        "[bold white]SCENARIO: The Junior Dev Fix (Basic Code Edit)[/bold white]\n"
        "[dim]The agent must identify a hardcoded bug and fix it surgically.[/dim]\n\n"
        "1. [cyan]app.py[/cyan]: Contains a 50% tax rate.\n"
        "[bold yellow]Challenge:[/bold yellow] Change the tax rate to 0.05 (5%) without breaking the function.",
        title="Capability: Code Modification", border_style="green"
    ))
    
    console.print("[bold]Original Code (app.py):[/bold]")
    console.print(Syntax(source_code, "python", theme="monokai", line_numbers=True))
    console.print(Rule(style="dim"))

    config = {"configurable": {"thread_id": "proof_code_basic"}, "recursion_limit": 100}
    
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
    
    # 4. Execution Loop
    for event in session.app.stream(session.state, config=config):
        node_name = list(event.keys())[0]
        node_output = event[node_name]
        
        # Get State
        current_state = session.app.get_state(config).values
        # Sync if not ready (sometimes get_state lags slightly behind stream yield?)
        if not current_state: current_state = session.state
            
        fw_state = current_state.get('framework_state')
        pager = session.pager
        
        # Determine Move
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

        # Only print row if we have a move (Manager) or an audit result
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

            # Check if file was edited (Success Condition)
            with open("app.py", "r") as f: content = f.read()
            if "0.05" in content and "0.5" not in content and node_name == "executor":
                console.print(Panel(
                    Syntax(content, "python", theme="monokai", line_numbers=True),
                    title="[bold green]SUCCESS: Code Patched[/bold green]",
                    border_style="green"
                ))
                break
        
        if turn_count > 12:
            console.print("[bold red]FAIL: Timeout or Agent failed to edit.[/bold red]")
            break

    # Cleanup
    if os.path.exists("app.py"): os.remove("app.py")

if __name__ == "__main__":
    run_code_basic_proof()