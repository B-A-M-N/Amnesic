import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.syntax import Syntax

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession

def run_persona_swap_proof():
    console = Console()
    
    # 1. Setup: Monolith needing decomposition
    with open("app.py", "w") as f:
        f.write("def process_order(order):\n"
                "    # Monolithic function\n"
                "    print(f\"Processing order {order['id']}\")\n"
                "    if order['price'] < 0:\n"
                "        raise ValueError(\"Invalid price\")\n"
                "    if not order['items']:\n"
                "        raise ValueError(\"No items\")\n\n"
                "    total = order['price'] * 1.08 # Tax\n\n"
                "    print(f\"Saving order {order['id']} with total {total}\")\n"
                "    return total\n")

    console.print(Panel(
        "[bold white]SCENARIO: The Spaghetti Decomposition (Persona Swap)[/bold white]\n"
        "[dim]The agent must first PLAN a refactor, then SWITCH to an implementation persona to execute it.[/dim]\n\n"
        "1. [cyan]Architect[/cyan]: Analyze the monolith. Create a plan to extract 3 functions: validate(), calculate(), save().\n"
        "2. [green]Implementer[/green]: Execute the plan found in the Artifacts.\n\n"
        "[bold yellow]Challenge:[/bold yellow] Use 'switch_strategy' to transition from high-level design to complex structural rewriting.",
        title="Capability 11: Persona Swap", border_style="blue"
    ))

    # 2. Initialize Session
    mission = (
        "MISSION: 1. Architect Mode: Read app.py. "
        "2. Create a REFACTOR_PLAN artifact specifying how to extract the validation logic into a new function 'validate_order'. "
        "3. Switch Strategy to 'IMPLEMENTER'. "
        "4. Implement the split in app.py. "
        "5. Halt once complete."
    )
    
    # Initial Strategy: The Architect
    initial_strategy = "PERSONA: Architect. FOCUS: Analysis and planning. Do NOT edit code yet."
    
    session = AmnesicSession(mission=mission, l1_capacity=32768, strategy=initial_strategy)
    config = {"configurable": {"thread_id": "proof_persona_spaghetti"}, "recursion_limit": 100}
    
    # Visual Confirmation
    session.visualize()
    
    turn_count = 0
    
    # 3. Telemetry Setup
    COLS = [
        ("Turn", "right", "cyan", 4),
        ("L1 Files", "center", "magenta", 12),
        ("L1 Toks", "center", "white", 10),
        ("Strategy", "left", "yellow", 20),
        ("Node", "left", "blue", 10),
        ("Manager Action", "left", "yellow", 25),
        ("Thought Process", "left", "italic dim", 40),
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
        
        strategy_label = "Architect 📐" if "Architect" in str(fw_state.strategy) else "Implementer 🛠️"

        if move:
            row_data = (
                str(turn_count),
                ", ".join(active_files) if active_files else "EMPTY",
                token_str,
                strategy_label,
                node_label,
                f"{move.tool_call}({move.target})" if move else "---",
                move.thought_process if move else "---",
                Text(audit_val, style=audit_style)
            )
            print_stream_row(row_data)

            if move.tool_call == "halt_and_ask":
                with open("app.py", "r") as f: content = f.read()
                # Check for structural changes
                if "def validate_order" in content:
                     console.print(Panel(
                         Syntax(content, "python", theme="monokai"),
                         title="[bold green]SUCCESS: Code Decomposed[/bold green]",
                         border_style="green"
                     ))
                else:
                     console.print(Panel(
                         Syntax(content, "python", theme="monokai"),
                         title="[bold red]FAIL: Decomposition incomplete.[/bold red]",
                         border_style="red"
                     ))
                break
        
        if turn_count > 20:
            console.print("[bold red]Timeout reached.[/bold red]")
            break

    # Cleanup
    if os.path.exists("app.py"): os.remove("app.py")

if __name__ == "__main__":
    run_persona_swap_proof()
