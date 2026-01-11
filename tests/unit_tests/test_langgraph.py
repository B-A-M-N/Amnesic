import sys
import os
import logging
from rich.console import Console

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from amnesic.core.session import AmnesicSession

def test_langgraph_boot():
    console = Console()
    console.print("[bold blue]Testing LangGraph Integration (AmnesicSession)...[/bold blue]")
    
    try:
        session = AmnesicSession(mission="Test System", root_dir=".")
        console.print("[green]✔ Graph Built Successfully[/green]")
        
        # We won't run a full chat because it requires a running Ollama instance 
        # and we want this test to be fast/safe. 
        # But we can verify the graph structure.
        
        nodes = session.app.get_graph().nodes
        assert "manager" in nodes
        assert "auditor" in nodes
        assert "executor" in nodes
        
        console.print("[green]✔ Nodes Verified[/green]")
        
        # Verify compiled app
        assert session.app is not None
        console.print("[green]✔ App Compiled[/green]")
        
    except Exception as e:
        console.print(f"[bold red]LangGraph Test Failed:[/bold red] {e}")
        raise e

if __name__ == "__main__":
    test_langgraph_boot()
