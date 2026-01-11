import os
import sys
import argparse
import json
import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.json import JSON
from rich.syntax import Syntax
from rich.table import Table

from amnesic import Manager, Auditor, NextMove

# --- CONFIGURATION ---
MODEL_NAME = "qwen2.5-coder:3b"
TELEMETRY_FILE = "amnesic_telemetry.jsonl"

console = Console()

def log_telemetry(event: str, details: dict):
    """Logs system events to a JSONL file for audit."""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "event": event,
        "details": details
    }
    with open(TELEMETRY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def scan_directory_recursive(path: str) -> list[str]:
    """Recursively finds all text-based source files."""
    file_list = []
    ignore_dirs = {".git", "__pycache__", ".gemini", "node_modules", "dist", "build", "venv", ".env", ".amnesic_cache"}
    ignore_exts = {".pyc", ".png", ".jpg", ".lock", ".pkl", ".bin"}
    
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if any(file.endswith(ext) for ext in ignore_exts):
                continue
            if "." in file: 
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, path)
                file_list.append(rel_path)
    return file_list

def execute_action(decision: NextMove, base_path: str):
    full_target_path = os.path.join(base_path, decision.target)
    
    if decision.action == "retrieve_file":
        console.print(Panel(f"Reading file: [bold cyan]{decision.target}[/bold cyan]", title="TOOL EXECUTION", style="yellow"))
        if os.path.exists(full_target_path):
            try:
                with open(full_target_path, 'r', errors='replace') as f:
                    content = f.read()
                syntax = Syntax(content[:500] + ("..." if len(content) > 500 else ""), "python", theme="monokai", line_numbers=True)
                console.print(syntax)
                return f"Content of {decision.target} (truncated):\n{content[:2000]}"
            except Exception as e:
                return f"Error reading {decision.target}: {str(e)}"
        else:
            return f"File {decision.target} not found."
            
    elif decision.action == "write_code":
        console.print(Panel(f"Targeting code change in: [bold cyan]{decision.target}[/bold cyan]", title="TOOL EXECUTION", style="yellow"))
        return f"Ready to write code to {decision.target}. (Simulation)"
        
    elif decision.action == "suspend_task":
        console.print(Panel(f"Reason: {decision.thought_process}", title="TASK SUSPENDED", style="red"))
        return "Task suspended."
    
    return "Action completed."

def main():
    parser = argparse.ArgumentParser(description="Amnesic: AI Governance Framework")
    parser.add_argument("path", nargs="?", default=".", help="Target directory to analyze (default: current)")
    parser.add_argument("--refresh", action="store_true", help="Force re-indexing of the codebase")
    args = parser.parse_args()
    
    target_path = os.path.abspath(args.path)
    if not os.path.isdir(target_path):
        console.print(f"[bold red]Error:[/bold red] Directory '{target_path}' does not exist.")
        sys.exit(1)

    console.print(Panel.fit(f"AMNESIC FRAMEWORK: DIY MVP\nTarget: [bold blue]{target_path}[/bold blue]", style="bold magenta", border_style="bright_blue"))
    
    # 1. Initialize Nodes
    try:
        with console.status("[bold green]Initializing Memory & Manager...[/bold green]"):
            manager = Manager(model_name=MODEL_NAME)
            # Cache dir specific to the target path to avoid collisions if running on different repos
            cache_name = f".amnesic_cache_{os.path.basename(target_path)}"
            auditor = Auditor(cache_dir=cache_name)
            
            # --- MEMORY INGESTION ---
            files = scan_directory_recursive(target_path)
            count, cached = auditor.index_files(files, force=args.refresh)
            
            if cached:
                console.print(f"[green]✔[/green] Loaded Memory Index ({count} files) from cache.")
            else:
                console.print(f"[green]✔[/green] Indexed {count} files into Memory.")
            
    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        sys.exit(1)

    # 2. Set Mission
    mission_goal = Prompt.ask("[bold green]Target Mission[/bold green]", default="Analyze the project structure")
    auditor.set_goal(mission_goal)
    console.print(f"[dim]Objective anchored: {mission_goal}[/dim]\n")
    log_telemetry("mission_start", {"goal": mission_goal, "target_path": target_path})
    
    history = []
    
    # 3. Main Loop
    while True:
        user_input = Prompt.ask("[bold cyan]User[/bold cyan]")
        
        if user_input.lower() in ["exit", "quit", "q"]:
            console.print("[bold red]Shutting down...[/bold red]")
            break
            
        history.append(f"User: {user_input}")
        history_str = "\n".join(history[-10:])
        
        # --- THE MEMORY TRICK ---
        context_query = f"{mission_goal} {user_input}"
        relevant_files = auditor.get_relevant_files(context_query, top_k=15)
        
        # Create a nice table for the relevant files
        if relevant_files:
            table = Table(title="Working Memory (Context)", show_header=False, box=None)
            for f in relevant_files:
                table.add_row(f"[dim]{f}[/dim]")
            console.print(table)
        
        file_map_str = "\n".join(relevant_files) if relevant_files else "(No files found)"
        
        # --- STEP 1: Manager Decides ---
        with console.status("[bold blue]Manager evaluating context...[/bold blue]"):
            try:
                decision = manager.decide(history_str, file_map_str)
            except Exception as e:
                console.print(f"[bold red]Manager Decision Error:[/bold red] {e}")
                continue

        console.print(Panel(JSON(decision.model_dump_json()), title="MANAGER PROPOSAL", border_style="blue"))
        log_telemetry("manager_proposal", decision.model_dump())
        
        # --- STEP 2: Auditor Checks ---
        drift_prompt = f"Action: {decision.action} on {decision.target}"
        drift_score = auditor.check_drift(drift_prompt)
        
        console.print(f"[bold]Auditor Drift Score:[/bold] {drift_score:.4f}")
        log_telemetry("auditor_check", {"drift_score": drift_score, "action": drift_prompt})

        if drift_score < 0.35: 
            console.print(Panel("⛔ BLOCK: Action Drifted from Goal", style="bold red"))
            feedback = f"Action blocked by Auditor. Focus on: {mission_goal}"
            history.append(f"System: {feedback}")
        else:
            console.print(Panel("✅ PASS: Action Aligned with Goal", style="bold green"))
            # --- STEP 3: Execution ---
            result = execute_action(decision, target_path)
            history.append(f"System: {result}")
            log_telemetry("execution", {"result": result})

if __name__ == "__main__":
    main()
