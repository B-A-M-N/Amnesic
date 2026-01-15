import os
import sys
import random
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_elastic_proof():
    console = Console()
    
    # 1. Setup: Multiple files that NEED to be seen together
    with open("config_base.py", "w") as f:
        f.write("BASE_VALUE = 100\n# Keep this in mind while reading others.")
    
    with open("module_a.py", "w") as f:
        f.write("MOD_A = 50\n# Relation: BASE_VALUE + MOD_A")

    console.print(Panel(
        "[bold white]SCENARIO: Cross-Document Reasoning (Elastic Context)[/bold white]\n"
        "[dim]The agent is allowed to hold multiple files in L1 simultaneously.[/dim]\n\n"
        "1. [cyan]config_base.py[/cyan]: Global constant.\n"
        "2. [green]module_a.py[/green]: Local logic.\n\n"
        "[bold yellow]Challenge:[/bold yellow] Keep config_base.py loaded while also staging module_a.py.\n"
        "This proves 'Strict Amnesia' is a policy choice, not a technical limitation.",
        title="Capability 12: Elastic Context",
        border_style="green"
    ))

    # 2. Initialize Session with elastic_mode=True
    mission = (
        "MISSION: Read config_base.py and module_a.py. "
        "Hold BOTH in memory to calculate the final sum. "
        "Do NOT unstage config_base.py until the mission is complete."
    )
    
    session = AmnesicSession(mission=mission, l1_capacity=3000, elastic_mode=True)
    config = {"configurable": {"thread_id": "proof_elastic"}, "recursion_limit": 100}
    
    session.visualize()
    
    turn_count = 0
    multi_file_detected = False
    
    # 3. Telemetry
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 Files", "center", "magenta", 25),
        ("L1 Toks", "center", "white", 10),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 40),
        ("Auditor", "center", None, 8)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Elastic Mission Execution Trace", style="bold green"))
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
        
        pager = session.pager
        move = node_output.get('manager_decision') if 'manager_decision' in node_output else current_state.get('manager_decision')
        audit = current_state.get('last_audit')
        
        active_files = [k.replace("FILE:", "") for k in pager.active_pages.keys() if "SYS:" not in k]
        
        # KEY VERIFICATION: Multiple files in L1
        if len(active_files) > 1:
            multi_file_detected = True
        
        token_str = f"{pager.current_usage}/{pager.capacity}"
        audit_val = audit["auditor_verdict"] if audit else "---"
        audit_style = "green" if "PASS" in str(audit_val) else "red" if "REJECT" in str(audit_val) else "white"

        if move:
            row_data = (
                str(turn_count),
                ", ".join(active_files) if active_files else "EMPTY",
                token_str,
                node_name,
                f"{move.tool_call}({move.target})",
                move.thought_process,
                Text(str(audit_val), style=audit_style)
            )
            print_stream_row(row_data)

            if move.tool_call == "halt_and_ask":
                if multi_file_detected:
                    console.print(Panel("[bold green]SUCCESS: Agent successfully managed multiple files in L1.[/bold green]"))
                else:
                    console.print(Panel("[bold red]FAIL: Agent behaved amnesically despite elastic_mode.[/bold red]"))
                break
        
        if turn_count > 15:
            console.print("[bold red]Timeout.[/bold red]")
            break

    # Cleanup
    for f in ["config_base.py", "module_a.py"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_elastic_proof()
