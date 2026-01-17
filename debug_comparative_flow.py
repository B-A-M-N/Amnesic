"""
RAW LOG DEBUGGER: Comparative Flow Reconstruction
Replicates Scenario 1 (Semantic Overflow) while printing every RAW interaction.
"""
import os
import sys
import json
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from langchain_core.messages import SystemMessage, HumanMessage

# Ensure framework access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from amnesic.core.session import AmnesicSession
from tests.comparative.shared import StandardReActAgent

console = Console()

def debug_standard_agent():
    console.print(Panel("DEBUGGING: Standard Agent (Sliding Window)", style="bold red"))
    
    val_a, val_b = 593, 886
    noise = "NOISE_FRAGMENT " * 150
    with open("vault_1.txt", "w") as f: f.write(f"ID_X: {val_a}\n{noise}")
    with open("vault_2.txt", "w") as f: f.write(f"ID_Y: {val_b}\n{noise}")
    
    mission = f"MISSION: Multiply ID_X ({val_a}) and ID_Y ({val_b})."
    std = StandardReActAgent(mission, token_limit=32768)
    
    # We intercept the driver.generate_structured call to see raw
    original_gen = std.driver.generate_structured
    
    def raw_gen_intercept(user_prompt, schema, system_prompt):
        console.print("\n[bold red]>>> RAW REQUEST TO LLM (Standard Agent)[/bold red]")
        console.print(f"[dim]--- SYSTEM ---\n{system_prompt[:300]}...[/dim]")
        console.print(f"[white]--- USER ---\n{user_prompt}[/white]")
        
        # Call actual invoke to see raw string
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        resp = std.driver._client.invoke(messages)
        
        console.print("\n[bold red]<<< RAW RESPONSE FROM LLM (Standard Agent)[/bold red]")
        console.print(f"[yellow]{resp.content}[/yellow]")
        
        # Continue with normal parsing
        return std.driver._extract_json_block(resp.content, schema)

    std.driver.generate_structured = raw_gen_intercept
    
    for i in range(3):
        console.print(Rule(f"Turn {i+1}"))
        std.step()

def debug_amnesic_agent():
    console.print(Panel("DEBUGGING: Amnesic Agent (Read-Then-Release)", style="bold green"))
    
    val_a, val_b = 593, 886
    mission = f"MISSION: Multiply ID_X ({val_a}) and ID_Y ({val_b})."
    session = AmnesicSession(mission=mission, l1_capacity=32768)
    
    # Intercept Amnesic Driver
    original_gen = session.driver.generate_structured
    
    def raw_gen_intercept(user_prompt, schema, system_prompt):
        console.print(f"\n[bold green]>>> RAW REQUEST TO LLM (Amnesic {schema.__name__})[/bold green]")
        console.print(f"[dim]--- SYSTEM ---\n{system_prompt[:400]}...[/dim]")
        console.print(f"[white]--- USER ---\n{user_prompt}[/white]")
        
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        resp = session.driver._client.invoke(messages)
        
        console.print(f"\n[bold green]<<< RAW RESPONSE FROM LLM (Amnesic {schema.__name__})[/bold green]")
        console.print(f"[cyan]{resp.content}[/cyan]")
        
        return session.driver._extract_json_block(resp.content, schema)

    session.driver.generate_structured = raw_gen_intercept
    
    turn = 0
    for event in session.app.stream(session.state, config={"configurable": {"thread_id": "debug"}}):
        if "manager" in event:
            turn += 1
            console.print(Rule(f"Manager Turn {turn}"))
        if "auditor" in event:
            console.print(Rule("Auditor Turn"))
        if turn >= 2: break

if __name__ == "__main__":
    debug_standard_agent()
    debug_amnesic_agent()
    
    # Cleanup
    for f in ["vault_1.txt", "vault_2.txt"]: 
        if os.path.exists(f): os.remove(f)
