import os
import sys
import logging
from rich.console import Console
from rich.panel import Panel

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from amnesic.core.session import AmnesicSession
from amnesic.core.sidecar import SharedSidecar

# Suppress noisy logs
logging.getLogger("amnesic").setLevel(logging.ERROR)

def run_context_swap_proof():
    console = Console()
    console.print(Panel.fit("[bold white]PROOF: CONTEXT SWAPPING & AUDIT PROFILES (8B OPTIMIZED)[/bold white]", border_style="blue"))

    # 0. Setup Environment
    SharedSidecar().reset()
    if os.path.exists("temp_src"):
        import shutil
        shutil.rmtree("temp_src")
    if os.path.exists("temp_empty"):
        shutil.rmtree("temp_empty")
        
    os.makedirs("temp_src", exist_ok=True)
    os.makedirs("temp_empty", exist_ok=True) # For the isolated agent

    # 1. Create Source Files (The "Haystack")
    files = {
        "temp_src/auth_system.py": "def authenticate_user(u, p):\n    # LEGACY AUTH\n    if u == 'admin' and p == '1234': return True\n    return False",
        "temp_src/db_connector.py": "def connect_db():\n    print('Connecting to MySQL 5.6...')\n    return 'db_connection'",
        "temp_src/tax_calculator.py": "def calculate_tax(amount):\n    # OLD RATE\n    return amount * 0.05",
        "temp_src/readme.txt": "Project contains auth, db, and tax logic."
    }
    for path, content in files.items():
        with open(path, "w") as f: f.write(content)

    # --- PHASE 1: THE SCOUT (FLUID MODE) ---
    console.print("\n[bold cyan]--- PHASE 1: THE SCOUT (FLUID_READ) ---[/bold cyan]")
    console.print("Goal: Rapidly scan files and extract key functions. High speed, low overhead.")
    
    # 8b-Friendly Prompt: Explicit steps, explicit tool syntax
    scout_mission = (
        "MISSION:\n"
        "1. Read 'temp_src/auth_system.py'. Extract the code. Save artifact 'AUTH_CODE'.\n"
        "2. Read 'temp_src/db_connector.py'. Extract the code. Save artifact 'DB_CODE'.\n"
        "3. Read 'temp_src/tax_calculator.py'. Extract the code. Save artifact 'TAX_CODE'.\n"
        "4. HALT.\n\n"
        "RULES:\n"
        "- Use 'stage_context(file)' then 'save_artifact(KEY: content)'.\n"
        "- You MUST stage the file before saving."
    )
    
    scout = AmnesicSession(
        mission=scout_mission,
        root_dir="temp_src",
        audit_profile="FLUID_READ", # Fast path enabled
        model="rnj-1:8b-cloud",
        base_url="http://localhost:11434"
        )
    
    try:
        # Higher recursion limit for 8b to recover from mistakes
        scout.run(config={"recursion_limit": 50, "configurable": {"thread_id": "scout"}})
    except Exception as e: 
        console.print(f"[dim]Scout stopped: {e}[/dim]")    
    # Verify Artifacts
    artifacts = {a.identifier: a.summary for a in scout.state['framework_state'].artifacts}
    console.print(f"[dim]Scout Artifacts: {list(artifacts.keys())}[/dim]")
    
    # --- PHASE 2: THE ARCHITECT (ISOLATED) ---
    console.print("\n[bold magenta]--- PHASE 2: THE ARCHITECT (ISOLATED) ---[/bold magenta]")
    console.print("Goal: Load offloaded context (without disk access) and plan a refactor.")
    
    # 8b-Friendly Prompt: Explicit distinction between Files and Artifacts
    architect_mission = (
        "MISSION:\n"
        "1. Use 'query_sidecar(CODE)' to see what is available.\n"
        "2. Use 'stage_multiple_artifacts(AUTH_CODE, DB_CODE, TAX_CODE)' to load them into RAM.\n"
        "3. Write a file 'refactor.md' with a plan to upgrade them (Postgres, SHA256, 10% tax).\n"
        "4. HALT.\n\n"
        "CRITICAL RULES:\n"
        "- You are in a Clean Room. You CANNOT use 'stage_context'.\n"
        "- You MUST use 'stage_artifact' or 'stage_multiple_artifacts'.\n"
        "- To write the plan, use: write_file('refactor.md: The plan content...')\n"
        "- Do NOT try to read source files. They do not exist here."
    )
    
    architect = AmnesicSession(
        mission=architect_mission,
        root_dir="temp_empty", # Physical Isolation
        audit_profile="STRICT_AUDIT", # Safety on
        sidecar=scout.sidecar, # Share the brain
        model="rnj-1:8b-cloud",
        base_url="http://localhost:11434"
        )
    
    try:
        architect.run(config={"recursion_limit": 50, "configurable": {"thread_id": "architect"}})
    except Exception as e:
        console.print(f"[dim]Architect stopped: {e}[/dim]")

    # --- PHASE 3: VERIFICATION ---
    console.print("\n[bold green]--- PHASE 3: VERIFICATION ---[/bold green]")
    
    plan_path = "temp_empty/refactor.md"
    if os.path.exists(plan_path):
        with open(plan_path) as f: content = f.read()
        console.print(Panel(content, title="Generated Plan"))
        
        required = ["SHA256", "Postgres", "tax"]
        hits = [k for k in required if k.lower() in content.lower()]
        
        if len(hits) >= 2:
             console.print("[bold green]PROOF SUCCESSFUL: Context swapped and synthesized![/bold green]")
        else:
             console.print(f"[bold yellow]PARTIAL SUCCESS: Plan generated but missing some keywords ({hits}).[/bold yellow]")
    else:
        console.print("[bold red]PROOF FAILED: No plan generated.[/bold red]")

    # Cleanup
    try:
        import shutil
        shutil.rmtree("temp_src")
        shutil.rmtree("temp_empty")
    except: pass

if __name__ == "__main__":
    run_context_swap_proof()
