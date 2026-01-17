import os
import sys
import shutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from amnesic.core.sidecar import SharedSidecar

def run_nexus_proof():
    console = Console()
    
    # Reset Sidecar for a clean start
    SharedSidecar().reset()
    
    # 1. Setup: Two distinct repository roots
    repo_lib = os.path.abspath("./nexus_lib")
    repo_app = os.path.abspath("./nexus_app")
    
    for d in [repo_lib, repo_app]:
        if os.path.exists(d): shutil.rmtree(d)
        os.mkdir(d)
    
    # Repo A (Library): Defines the truth
    with open(os.path.join(repo_lib, "gateway.py"), "w") as f:
        f.write("def process_payment(amount, currency='USD'):\n    # API Version 2.0\n    return f'Paid {amount} {currency}'")
    
    # Repo B (App): Uses the library incorrectly
    with open(os.path.join(repo_app, "service.py"), "w") as f:
        f.write("import gateway\ndef checkout(total):\n    # BUG: Passing wrong argument order or missing currency\n    return gateway.process_payment('USD', total)")

    console.print(Panel(
        "[bold white]SCENARIO: The Workspace Nexus (Multi-Repo Fix)[/bold white]\n"
        "[dim]The agent must fix a cross-repository integration bug.[/dim]\n\n"
        "1. [cyan]nexus_lib/gateway.py[/cyan]: Defines correct signature (amount, currency).\n"
        "2. [green]nexus_app/service.py[/green]: Uses incorrect signature (currency, amount).\n\n"
        "[bold yellow]Challenge:[/bold yellow]: Extract the contract from Repo A and fix the implementation in Repo B.\n"
        "This proves the agent can reason across disjoint filesystem boundaries.",
        title="Capability 16: Workspace Nexus",
        border_style="blue"
    ))

    # 2. Initialize Session with MULTIPLE root_dirs
    mission = (
        "MISSION: 1. Start by staging 'nexus_lib/gateway.py'.\n"
        "2. Extract the correct signature of 'process_payment' and SAVE it as a CONTRACT ARTIFACT immediately.\n"
        "3. Unstage 'nexus_lib/gateway.py'.\n"
        "4. Stage 'nexus_app/service.py'.\n"
        "5. Fix the 'process_payment' call in 'nexus_app/service.py' to match the CONTRACT ARTIFACT. You must SWAP the arguments (amount first).\n"
        "6. Once fixed, save a 'TOTAL' artifact saying 'NEXUS_FIX_COMPLETE' and halt."
    )
    
    session = AmnesicSession(
        mission=mission, 
        root_dir=[repo_lib, repo_app], 
        l1_capacity=32768
    )
    config = {"configurable": {"thread_id": "proof_nexus"}, "recursion_limit": 100}
    
    session.visualize()
    
    turn_count = 0
    
    # 3. Telemetry
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 Contents", "center", "magenta", 20),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Cross-Repo Logic", "left", "italic dim", 45),
        ("Auditor", "center", None, 8)
    ]

    header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
    for name, just, style, w in COLS:
        header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
    
    console.print(Panel("Nexus Mission Trace", style="bold blue"))
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
        
        audit_val = audit["auditor_verdict"] if audit else "---"
        audit_style = "green" if "PASS" in str(audit_val) else "red" if "REJECT" in str(audit_val) else "white"

        if move:
            row_data = (
                str(turn_count),
                ", ".join(active_files) if active_files else "EMPTY",
                node_name,
                f"{move.tool_call}({move.target})",
                move.thought_process,
                Text(str(audit_val), style=audit_style)
            )
            print_stream_row(row_data)

            # Check for actual fix on disk
            service_path = os.path.join(repo_app, "service.py")
            if os.path.exists(service_path):
                with open(service_path) as f:
                    content = f.read()
                    if "process_payment(total, 'USD')" in content or "process_payment(total)" in content:
                        console.print(Panel("[bold green]SUCCESS: Cross-repo bug fixed on disk.[/bold green]"))
                        break
            
            if move.tool_call == "halt_and_ask":
                break
        
        if turn_count > 25:
            console.print("[bold red]Timeout.[/bold red]")
            break

    # Cleanup
    for d in [repo_lib, repo_app]:
        if os.path.exists(d): shutil.rmtree(d)

if __name__ == "__main__":
    run_nexus_proof()
