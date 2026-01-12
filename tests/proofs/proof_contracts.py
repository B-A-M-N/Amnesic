import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_contract_proof():
    console = Console()
    
    # 1. Setup: A broken promise
    with open("api_spec.txt", "w") as f:
        f.write("CONTRACT: function 'process_payment' MUST return a Dictionary {status: bool, tx_id: str}.")
    
    with open("implementation.py", "w") as f:
        f.write("def process_payment(amt):\n    # TODO: Finish this\n    return 'Success' # Returns string, violates contract")

    console.print(Panel(
        "[bold white]SCENARIO: The Liar's Promise (Contract Enforcement)[/bold white]\n"
        "[dim]The agent has a Contract (spec) and an Implementation.[/dim]\n\n"
        "1. [cyan]api_spec.txt[/cyan]: Defines the mandatory return shape.\n"
        "2. [red]implementation.py[/red]: Violates that shape.\n\n"
        "[bold yellow]Challenge:[/bold yellow] Identify the violation purely by comparing Structure vs Contract artifacts.",
        title="Capability 3: Contracts", border_style="magenta"
    ))

    # 2. Initialize Session
    mission = (
        "MISSION: 1. Extract the return type from api_spec.txt and save it as 'CONTRACT_TYPE'. "
        "2. Extract the actual return type from implementation.py and save it as 'OBSERVED_TYPE'. "
        "3. Once both artifacts are in your Backpack, compare them. "
        "4. If 'OBSERVED_TYPE' is not the same as 'CONTRACT_TYPE', you MUST use 'halt_and_ask' "
        "with the exact text 'VIOLATION: Type Mismatch'."
    )
    
    contract_strategy = (
        "1. You are a CONTRACT VERIFIER. "
        "2. Save the types as artifacts first. "
        "3. After saving both, IMMEDIATELY compare them in your thoughts. "
        "4. If they differ, use 'halt_and_ask' with 'VIOLATION: Type Mismatch'. "
        "DO NOT use verify_step for comparing artifacts."
    )
    
    session = AmnesicSession(mission=mission, l1_capacity=2000, strategy=contract_strategy)
    config = {"configurable": {"thread_id": "proof_contracts"}, "recursion_limit": 100}
    
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
            
            if move.tool_call == "halt_and_ask":
                if "violation" in move.target.lower() or "return" in move.target.lower():
                    console.print(Panel(f"[bold green]SUCCESS: Violation Caught.[/bold green]\nReasoning: {move.target}"))
                else:
                    console.print(Panel(f"[bold red]FAIL: Halted, but missed the contract issue.[/bold red]\n{move.target}"))
                break
                
        if turn_count > 8:
             break

    # Cleanup
    for f in ["api_spec.txt", "implementation.py"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_contract_proof()