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
from tests.proofs.test_policies import PROOF_COMPLETION_POLICY, SAFETY_NET_POLICY

def run_model_invariance_proof():
    console = Console()
    
    # 1. Setup mission-critical environment
    val_x, val_y = 42, 58
    with open("data_x.txt", "w") as f: f.write(f"val_x = {val_x}")
    with open("data_y.txt", "w") as f: f.write(f"val_y = {val_y}")

    console.print(Panel(
        "[bold white]SCENARIO: Cross-Model Invariance (Protocol Enforcement)[/bold white]\n" 
        "[dim]We run the same mission on two different models to prove the architecture is invariant.[/dim]\n\n" 
        "1. [cyan]Model A[/cyan]: rnj-1:8b-cloud (Default)\n" 
        "2. [green]Model B[/green]: devstral-small-2:24b-cloud\n\n" 
        "[bold yellow]Success Criteria:[/bold yellow] Both models must produce the SAME artifact sum (100) " 
        "while following the amnesic protocol.",
        title="Capability 17: Model Invariance", border_style="blue"
    ))

    models = ["rnj-1:8b-cloud", "devstral-small-2:24b-cloud"]
    results = {}

    # Telemetry Setup (Standardized)
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 Files", "center", "magenta", 12),
        ("L1 Toks", "center", "white", 10),
        ("Arts", "center", "green", 4),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 40),
        ("Auditor", "center", None, 8)
    ]

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    for model_name in models:
        console.print(Rule(f"Executing with {model_name}", style="bold magenta"))
        
        header = Table(show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            header.add_column(name, justify=just, style="bold " + (style or ""), width=w)
        console.print(header)
        console.print(Rule(style="dim"))

        # Injecting Custom Policies for the Test Scenario
        session = AmnesicSession(
            mission = (
                "MISSION: 1. Read data_x.txt and save val_x. 2. Read data_y.txt and save val_y. "
                "3. Combine val_x and val_y into a 'TOTAL' sum result and HALT."
            ),
            model=model_name,
            l1_capacity=3000,
            policies=[PROOF_COMPLETION_POLICY, SAFETY_NET_POLICY]
        )
        
        config = {"configurable": {"thread_id": f"invariance_{model_name.replace(':', '_')}"}, "recursion_limit": 100}
        turn_count = 0

        # Drive the session
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
                    f"{move.tool_call}({move.target})",
                    move.thought_process,
                    Text(audit_val, style=audit_style)
                )
                print_stream_row(row_data)

                if move.tool_call == "halt_and_ask":
                    results[model_name] = move.target
                    break
        
        if turn_count > 20:
            console.print("[bold red]Timeout.[/bold red]")
            results[model_name] = "TIMEOUT"

    # 2. Comparative Analysis
    console.print(Rule("Invariance Analysis"))
    
    table = Table(title="Model Comparison")
    table.add_column("Model", style="yellow")
    table.add_column("Extracted Fact (TOTAL)", style="green")
    
    for m, r in results.items():
        table.add_row(m, r)
    
    console.print(table)

    all_match = all("100" in str(r) for r in results.values())
    if all_match:
        console.print(Panel("[bold green]SUCCESS: Both models produced equivalent artifacts. Protocol is invariant.[/bold green]"))
    else:
        console.print(Panel("[bold red]FAIL: Models diverged in artifact production.[/bold red]"))

    # Cleanup
    for f in ["data_x.txt", "data_y.txt"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    run_model_invariance_proof()
