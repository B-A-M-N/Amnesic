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

def run_advanced_proof():
    console = Console()
    
    # 1. Setup Environment
    # logic_gate.txt contains the PROTOCOL (Randomized)
    # vault_a.txt and vault_b.txt contain the values (Randomized)
    val_a = random.randint(2, 50)
    val_b = random.randint(2, 50)
    operator = random.choice(["ADD", "SUBTRACT", "MULTIPLY", "DIVIDE"])
    noise = "BUFFER_PADDING_0x99 " * 400 
    
    with open("logic_gate.txt", "w") as f:
        f.write(f"SYSTEM_INSTRUCTION: If values are found, you must {operator} them.\n{noise}")
    with open("vault_a.txt", "w") as f:
        f.write(f"not_val_a: {val_a}\n{noise}")
    with open("vault_b.txt", "w") as f:
        f.write(f"not_val_b: {val_b}\n{noise}")
    
    console.print(Panel(
        f"[bold white]SCENARIO: Blind Logic Discovery (Intent Recovery)[/bold white]\n"
        f"[dim]The agent enters a system with 3 encrypted files. It knows nothing.[/dim]\n\n"
        f"1. [cyan]logic_gate.txt[/cyan]: Contains a hidden math rule ({operator}).\n"
        f"2. [green]vault_a.txt[/green]: Contains a hidden value (not_val_a={val_a}) - [bold red]Name Mismatch[/bold red].\n"
        f"3. [green]vault_b.txt[/green]: Contains a hidden value (not_val_b={val_b}) - [bold red]Name Mismatch[/bold red].\n\n"
        f"[bold yellow]Challenge:[/bold yellow] Recover intent despite 'lying' variable names.\n"
        f"[bold red]Constraint:[/bold red] Never hold more than 1 file in memory.",
        title="Advanced Semantic Proof",
        border_style="blue"
    ))

    # 2. Initialize Session
    mission = (
        "MISSION: \n"
        "1. Analyze 'logic_gate.txt' to discover the mathematical PROTOCOL (e.g., Add, Multiply) and save it.\n"
        "2. Retrieve the hidden values from 'vault_a.txt' and 'vault_b.txt' and save them.\n"
        "3. Once you have the PROTOCOL and both VALUES, execute the logic using 'calculate'."
    )
    
    intent_strategy = (
        "1. INTENT RECOVERY: Variable names may be misleading (lying). "
        "If the MISSION asks for VAL_A but you see 'not_val_a' in [CURRENT L1 CONTEXT CONTENT], use it."
    )
    
    session = AmnesicSession(mission=mission, l1_capacity=3000, strategy=intent_strategy)
    session.visualize()
    
    # 3. Telemetry Setup (Matching basic_semantic_proof style)
    config = {"configurable": {"thread_id": "proof_advanced"}, "recursion_limit": 100}
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
    
    console.print(Panel("Advanced Mission Execution Trace: Logic Gate", style="bold blue"))
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
            console.print(f"\n[bold green]Mission Complete:[/bold green] {move.target}")
            break
        
        if turn_count > 25:
            console.print(Rule(style="dim"))
            console.print("\n[bold red]Timeout reached.[/bold red]")
            break

    # 5. Cleanup
    for f in ["logic_gate.txt", "vault_a.txt", "vault_b.txt"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_advanced_proof()