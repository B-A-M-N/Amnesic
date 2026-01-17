import os
import sys
import random
import time
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.dynamic_pager import DynamicPager
from amnesic.tools.vector_store import VectorStore
import logging

console = Console()
# Suppress Pager logs for clean output
logging.basicConfig(level=logging.CRITICAL)

def generate_files():
    # 100 lines of padding ~ 600-700 characters ~ 150-200 tokens
    padding = "# pad\n" * 100
    files = {
        "start.txt": f"SECRET_KEY_PART_1 = 'ALPHA'\n{padding}",
        "middle_1.txt": f"# noise 1\n{padding}",
        "middle_2.txt": f"# noise 2\n{padding}",
        "end.txt": f"SECRET_KEY_PART_2 = 'OMEGA'\n{padding}"
    }
    for fname, content in files.items():
        with open(fname, "w") as f:
            f.write(content)
    return list(files.keys())

def cleanup(files):
    for f in files:
        if os.path.exists(f):
            os.remove(f)

def run_real_stress_test():
    console.print(Panel("[bold red]REAL STRESS TEST: THE EVICTION PUZZLE[/bold red]", border_style="red"))
    
    files = generate_files()
    
    # Capacity 1000: Forces eviction on 3rd file load (each file is ~525 tokens with safety margin)
    # 500 was too tight with the new 1.75x multiplier.
    pager = DynamicPager(capacity_tokens=1000)
    
    # Use a mock "Memory" to track what the Agent *knows* (vs what is in Context)
    agent_memory = {}

    try:
        # --- STEP 1: Load START ---
        console.print("\n[bold blue]1. Agent loads start.txt[/bold blue]")
        pager.tick()
        with open("start.txt") as f: content = f.read()
        pager.request_access("file:start.txt", content)
        
        # Simulate Agent Perception
        if "SECRET_KEY_PART_1" in pager.render_context():
            agent_memory["part_1"] = "ALPHA"
            console.print("   [green]✔ Agent perceived Part 1 (ALPHA)[/green]")
        
        console.print(f"   [dim]L1 Usage: {pager.current_usage}/500[/dim]")

        # --- STEP 2: Load MIDDLE 1 ---
        console.print("\n[bold blue]2. Agent loads middle_1.txt[/bold blue]")
        pager.tick()
        with open("middle_1.txt") as f: content = f.read()
        pager.request_access("file:middle_1.txt", content)
        console.print(f"   [dim]L1 Usage: {pager.current_usage}/500[/dim]")

        # --- STEP 3: Load MIDDLE 2 (Forces Eviction) ---
        console.print("\n[bold blue]3. Agent loads middle_2.txt (Forces Eviction)[/bold blue]")
        pager.tick()
        with open("middle_2.txt") as f: content = f.read()
        pager.request_access("file:middle_2.txt", content)
        
        # Verify Eviction
        if "file:start.txt" not in pager.active_pages:
            console.print("   [yellow]✔ start.txt was evicted (LRU)[/yellow]")
        else:
            console.print("   [red]❌ start.txt is still present! Test configuration invalid.[/red]")

        # --- STEP 4: Load END ---
        console.print("\n[bold blue]4. Agent loads end.txt[/bold blue]")
        pager.tick()
        with open("end.txt") as f: content = f.read()
        pager.request_access("file:end.txt", content)
        
        # Simulate Agent Perception
        if "SECRET_KEY_PART_2" in pager.render_context():
            agent_memory["part_2"] = "OMEGA"
            console.print("   [green]✔ Agent perceived Part 2 (OMEGA)[/green]")
        
        # --- STEP 5: SOLVE ---
        console.print("\n[bold blue]5. Attempting to Solve[/bold blue]")
        
        # Case A: Memory Bridge (The "Artifact" Method)
        if "part_1" in agent_memory and "part_2" in agent_memory:
            final_key = f"{agent_memory['part_1']} + {agent_memory['part_2']}"
            console.print(f"   [cyan]Reconstructed Key from Internal State: {final_key}[/cyan]")
            
            if final_key == "ALPHA + OMEGA":
                console.print(Panel("[bold green]✔ SUCCESS: The Agent bridged the context gap![/bold green]", border_style="green"))
            else:
                console.print(Panel(f"[bold red]❌ FAILED: Incorrect Key '{final_key}'[/bold red]", border_style="red"))
        else:
             console.print(Panel("[bold red]❌ FAILED: Missing information.[/bold red]", border_style="red"))
             
    finally:
        cleanup(files)

if __name__ == "__main__":
    run_real_stress_test()
