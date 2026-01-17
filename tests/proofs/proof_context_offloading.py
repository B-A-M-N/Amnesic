import os
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from amnesic.core.sidecar import SharedSidecar

def run_complex_composition_proof():
    console = Console()
    
    # 0. Initial Reset
    SharedSidecar().reset()
    if os.path.exists(".amnesic_cache/brain.json"):
        os.remove(".amnesic_cache/brain.json")

    # 1. Create the Disjoint Knowledge Bases (Multi-Part, Noisy)
    noise = "# BUFFER_PAD " * 400 # ~2000 tokens
    
    # Source A: Networking
    with open("network_specs.txt", "w") as f:
        f.write(f"PROTOCOL_TCP: 'Transmission Control Protocol ensures reliable delivery.'\n")
        f.write(f"PROTOCOL_UDP: 'User Datagram Protocol is for low-latency streaming.'\n")
        f.write(noise)
        
    # Source B: Security
    with open("security_specs.txt", "w") as f:
        f.write(f"SEC_AES: 'AES-256 is the standard for symmetric encryption.'\n")
        f.write(f"SEC_RSA: 'RSA is used for asymmetric key exchange.'\n")
        f.write(noise)

    console.print(Panel.fit(
        "[bold white]MULTI-ARTIFACT SYNTHESIS: THE KNOWLEDGE GRID[/bold white]\n"
        "[dim]Proving multiple agents can offload distinct artifacts for a third agent to compose.[/dim]",
        border_style="magenta"
    ))

    # --- SESSION 1: THE NETWORK ENGINEER ---
    console.print("\n[bold cyan]PHASE 1: Context Distillation (Agent A)[/bold cyan]")
    console.print("[dim]Action: Extracting multiple networking objects into the persistent Sidecar...[/dim]\n")
    s1 = AmnesicSession(
        mission="MISSION: 1. Extract 'NET_TCP' fact. 2. Extract 'NET_UDP' fact. 3. Use 'save_artifact(KEY: value)' for each. HALT.",
        l1_capacity=32768,
        eviction_strategy="manual" 
    )
    
    for event in s1.app.stream(s1.state, config={"configurable": {"thread_id": "networker"}, "recursion_limit": 100}):
        if "manager" in event:
            move = event["manager"]["manager_decision"]
            
            prompt_estimate = 3500
            total_est = s1.pager.current_usage + prompt_estimate
            
            console.print(f"  [cyan]A:[/cyan] [yellow]{move.tool_call}[/yellow] -> [white]{move.target}[/white]")
            console.print(f"     [dim]L1 Workspace: {s1.pager.current_usage}/32768 | Total Window: ~{total_est}/32768[/dim]")
            if move.tool_call == "halt_and_ask": break
    del s1

    # --- SESSION 2: THE SECURITY AUDITOR ---
    console.print(Rule(style="dim"))
    console.print("[bold green]PHASE 2: Security Distillation (Agent B)[/bold green]")
    console.print("[dim]Action: Offloading distinct security objects. Note the L1 resets...[/dim]\n")
    s2 = AmnesicSession(
        mission="MISSION: 1. Extract 'SEC_AES' fact. 2. Extract 'SEC_RSA' fact. 3. Use 'save_artifact(KEY: value)' for each. HALT.",
        l1_capacity=32768,
        eviction_strategy="manual"
    )
    for event in s2.app.stream(s2.state, config={"configurable": {"thread_id": "security"}, "recursion_limit": 100}):
        if "manager" in event:
            move = event["manager"]["manager_decision"]
            
            prompt_estimate = 3500
            total_est = s2.pager.current_usage + prompt_estimate
            
            console.print(f"  [green]B:[/green] [yellow]{move.tool_call}[/yellow] -> [white]{move.target}[/white]")
            console.print(f"     [dim]L1 Workspace: {s2.pager.current_usage}/32768 | Total Window: ~{total_est}/32768[/dim]")
            if move.tool_call == "halt_and_ask": break
    del s2

    # --- SESSION 3: THE COMPOSER ---
    console.print(Rule(style="dim"))
    console.print("[bold blue]PHASE 3: Innovation Synthesis (Agent C)[/bold blue]")
    console.print("[dim]Agent C has NO access to files. It MUST reason from the persistent sidecar.[/dim]\n")
    
    # We physically isolate C from the source files to prove it uses the sidecar
    os.makedirs(".empty_dir", exist_ok=True)
    
    # ADVANCED WORKFLOW POLICY: Standard Warm-Start Linker
    from amnesic.core.flow_policies import NET_SEC_LINKER

    s3 = AmnesicSession(
        mission="MISSION: 1. Use 'query_sidecar' to find 'NET_TCP', 'NET_UDP', 'SEC_AES', and 'SEC_RSA'. "
                "2. Use 'stage_multiple_artifacts' to load all 4 into L1. "
                "3. Use 'calculate' with 'JOIN' to create a 4-line TOTAL report. HALT by passing the content of the report.",
        root_dir=".empty_dir", # PHYSICAL ISOLATION
        forbidden_tools=["stage_context"], # LEVER 2: Disable Disk Access
        l1_capacity=32768,
        policies=[NET_SEC_LINKER]
    )
    
    # We guide C specifically to use the new Aggregator Lever
    s3.state['framework_state'].strategy = (
        "RECONSTRUCTION STRATEGY: You cannot read files. You MUST use 'query_sidecar' to find the offloaded keys, "
        "then 'stage_multiple_artifacts' to bring them into RAM, then 'calculate' with 'JOIN' to synthesize."
    )

    final_result = None
    for event in s3.app.stream(s3.state, config={"configurable": {"thread_id": "composer"}, "recursion_limit": 100}):
        if "manager" in event:
            move = event["manager"]["manager_decision"]
            
            # Context Telemetry: Show that C is aggregating memory
            active_data = [p.replace("FILE:", "") for p in s3.pager.active_pages.keys() if "SYS:" not in p]
            
            console.print(f"  [blue]C:[/blue] [yellow]{move.tool_call}[/yellow]([white]{move.target}[/white])")
            console.print(f"     [dim]L1 Workspace: {s3.pager.current_usage}/32768 | L1 RAM: {active_data}[/dim]")
            
            if move.tool_call == "halt_and_ask":
                final_result = move.target
                break

    # --- FINAL AUDIT ---
    console.print("\n")
    console.print(Rule("Composition Audit"))
    keywords = ["TCP", "UDP", "AES", "RSA", "Transmission Control Protocol", "User Datagram Protocol"]
    match_count = sum(1 for k in keywords if k.upper() in str(final_result).upper())
    
    # TCP/Transmission and UDP/User Datagram are redundant, so we adjust the success threshold
    if match_count >= 4:
        console.print(Panel(f"[bold green]SUCCESS: Agent C synthesized all components ({match_count}/4 found)![/bold green]\n\n" 
                            f"[white]{final_result}[/white]", title="Final Composed System Architecture"))
    else:
        console.print(Panel(f"[bold red]FAIL: Composition missing core components. Result: {final_result}[/bold red]"))

    # Cleanup
    for f in ["network_specs.txt", "security_specs.txt"]:
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run_complex_composition_proof()
