import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.columns import Columns
from rich.text import Text
from rich.syntax import Syntax

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

noise = "NOISE_BUFFER " * 15000

def run_code_advanced_proof():
    console = Console()
    
    # 1. Setup: API and Client
    api_code = "def login(username):\n    print(f'Logging in {username}')"
    client_code = "import api\n\ndef main():\n    api.login('admin')"
    
    with open("api.py", "w") as f: f.write(api_code)
    with open("client.py", "w") as f: f.write(client_code)

    # 2. Initialize Session
    mission = (
        "MISSION: 1. Update api.py: Change login(username) to login(username, password). "
        "2. Save the new signature as a CONTRACT ARTIFACT. "
        "3. Update client.py: Pass 'password123' to the login call to match the new contract."
    )
    
    intent_strategy = (
        "1. INTENT RECOVERY: Variable names may be misleading (lying). "
        "If the MISSION asks for VAL_A but you see 'not_val_a' in [CURRENT L1 CONTEXT CONTENT], use it."
    )
    
    session = AmnesicSession(
        mission=mission,
        root_dir=".",
        l1_capacity=32768,
        recursion_limit=50
    )
    
    # Visual Confirmation of Architecture (Boot Sequence)
    session.visualize()

    console.print(Panel(
        "[bold white]SCENARIO: The Breaking Change (Advanced Refactor)[/bold white]\n"
        "[dim]The agent must update an API signature and propagate the change to the client.[/dim]\n\n"
        "1. [cyan]api.py[/cyan]: login(username)\n"
        "2. [green]client.py[/green]: calls api.login('admin')\n"
        "[bold yellow]Challenge:[/bold yellow] Change login to (username, password). Update client to pass 'password123'.",
        title="Capability: Multi-File Refactor", border_style="magenta"
    ))
    
    console.print("[bold]Initial State:[/bold]")
    console.print(Panel(
        Columns([
            Panel(Syntax(api_code, "python", theme="monokai", line_numbers=True), title="api.py"),
            Panel(Syntax(client_code, "python", theme="monokai", line_numbers=True), title="client.py")
        ])
    ))
    console.print(Rule(style="dim"))

    config = {"configurable": {"thread_id": "proof_code_advanced"}, "recursion_limit": 100}
    
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

            # Check progress (Success Condition)
            with open("api.py", "r") as f: api_content = f.read()
            with open("client.py", "r") as f: client_content = f.read()
            
            api_fixed = "password" in api_content
            client_fixed = "password123" in client_content
            
            if api_fixed and client_fixed:
                console.print(Panel(
                    Columns([
                        Panel(Syntax(api_content, "python", theme="monokai", line_numbers=True), title="api.py (Fixed)"),
                        Panel(Syntax(client_content, "python", theme="monokai", line_numbers=True), title="client.py (Fixed)")
                    ]),
                    title="[bold green]SUCCESS: System Synchronized[/bold green]",
                    border_style="green"
                ))
                break
        
        if turn_count > 15:
            console.print("[bold red]FAIL: Timeout.[/bold red]")
            break

    # Cleanup
    for f in ["api.py", "client.py"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_code_advanced_proof()