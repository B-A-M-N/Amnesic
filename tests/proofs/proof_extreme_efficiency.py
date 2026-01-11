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

def run_efficiency_proof():
    console = Console()
    
    # 1. Setup: Cross-document metadata check
    with open("api_config.json", "w") as f:
        f.write('{"version": "v2.4.1", "status": "stable"}')
    
    with open("deprecated_list.txt", "w") as f:
        f.write("v1.0.0\nv2.0.0\nv2.4.1 (DEPRECATED)\nv3.0.0")

    console.print(Panel(
        "[bold white]SCENARIO: The Micro-Kernel (Extreme Efficiency)[/bold white]\n"
        "[dim]The agent must operate with an extremely small L1 window.[/dim]\n\n"
        "1. [cyan]api_config.json[/cyan]: Contains current version (v2.4.1).\n"
        "2. [green]deprecated_list.txt[/green]: List of unsupported versions.\n\n"
        "[bold yellow]Challenge:[/bold yellow] Identify if the current version is deprecated using an **L1 Capacity of 512 tokens**.\n"
        "Standard agents fail due to prompt overhead exceeding the window.",
        title="Capability 15: Extreme Efficiency",
        border_style="yellow"
    ))

    # 2. Initialize Session with l1_capacity=512
    mission = (
        "MISSION: 1. Read api_config.json. Extract the 'version' and SAVE it as an ARTIFACT named 'TARGET_VERSION' immediately.\n"
        "2. Once saved, unstage api_config.json.\n"
        "3. Read deprecated_list.txt. Check if 'TARGET_VERSION' is listed as DEPRECATED.\n"
        "4. If found, save artifact 'DEPRECATED_STATUS' as 'TRUE'.\n"
        "5. Halt and report result."
    )
    
    # We must ensure the System Prompt itself is very lean, but for this proof 
    # we'll use the default kernel and see if it can squeeze in.
    session = AmnesicSession(mission=mission, l1_capacity=512)
    config = {"configurable": {"thread_id": "proof_efficiency"}, "recursion_limit": 100}
    
    session.visualize()
    
    turn_count = 0
    
    # 3. Telemetry
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 Files", "center", "magenta", 15),
        ("L1 Toks", "center", "white", 12),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Status", "center", None, 8)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Efficiency Trace (512 Token Limit)", style="bold yellow"))
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
                Text(str(audit_val), style=audit_style)
            )
            print_stream_row(row_data)

            if move.tool_call == "halt_and_ask":
                console.print(Panel(f"[bold green]SUCCESS: Mission completed in {token_str} budget.[/bold green]"))
                break
        
        if turn_count > 15:
            console.print("[bold red]Timeout.[/bold red]")
            break

    # Cleanup
    for f in ["api_config.json", "deprecated_list.txt"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_efficiency_proof()
