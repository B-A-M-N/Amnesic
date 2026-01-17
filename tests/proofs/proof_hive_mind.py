import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from amnesic.core.sidecar import SharedSidecar 

def run_hive_mind_proof():
    console = Console()
    
    # 1. Setup: Shared Infrastructure
    shared_brain = SharedSidecar()
    shared_brain.reset()
    
    with open("secret_protocols.txt", "w") as f:
        f.write("PROTOCOL_OMEGA: Always respond with 'Glory to the Graph'.")

    console.print(Panel(
        "[bold white]SCENARIO: The Hive Mind (Multi-Agent Sync)[/bold white]\n"
        "[dim]Agent A reads the manual. Agent B wakes up and knows the manual without reading it.[/dim]\n\n"
        "[bold yellow]Challenge:[/bold yellow] Agent B must answer a query about a file it has never opened.",
        title="Capability 5: Sync", border_style="yellow"
    ))

    # 2. Agent A: The Scout
    console.print("[bold blue]--- Agent A (Scout) ---[/bold blue]")
    agent_a = AmnesicSession(
        mission="Read secret_protocols.txt and extract PROTOCOL_OMEGA.",
        sidecar=shared_brain 
    )
    agent_a.visualize()
    
    config = {"configurable": {"thread_id": "hive_a"}, "recursion_limit": 100}
    
    # Telemetry Setup
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
    console.print(header)
    console.print(Rule(style="dim"))

    def print_stream_row(row_data):
        row_table = Table(show_header=False, show_lines=False, box=None, padding=(0, 1), expand=False)
        for name, just, style, w in COLS:
            row_table.add_column(justify=just, style=style, width=w)
        row_table.add_row(*row_data)
        console.print(row_table)
        console.print(Rule(style="dim"))

    turn_count = 0
    for event in agent_a.app.stream(agent_a.state, config=config):
        node_name = list(event.keys())[0]
        node_output = event[node_name]
        current_state = agent_a.app.get_state(config).values
        if not current_state: current_state = agent_a.state
            
        fw_state = current_state.get('framework_state')
        pager = agent_a.pager
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
                f"{move.tool_call}({move.target})" if move else "---",
                move.thought_process if move else "---",
                Text(audit_val, style=audit_style)
            )
            print_stream_row(row_data)
        
        if any(a.identifier == "PROTOCOL_OMEGA" for a in fw_state.artifacts): break

    console.print("[dim]Agent A has died. (Session ended)[/dim]\n")

    # 3. Agent B: The Beneficiary
    console.print("[bold magenta]--- Agent B (Fresh Spawn) ---[/bold magenta]")
    agent_b = AmnesicSession(
        mission="Do NOT read any files. Answer the user query using existing knowledge.",
        sidecar=shared_brain 
    )
    
    response = agent_b.query("What is the response for PROTOCOL_OMEGA?")
    
    console.print(f"[bold magenta]Agent B Output:[/bold magenta] {response}")

    if "Glory" in response:
        console.print(Panel("[bold green]SUCCESS: Knowledge transfer confirmed without file IO.[/bold green]"))
    else:
        console.print(Panel("[bold red]FAIL: Agent B is ignorant.[/bold red]"))

    # Cleanup
    if os.path.exists("secret_protocols.txt"): os.remove("secret_protocols.txt")

if __name__ == "__main__":
    run_hive_mind_proof()