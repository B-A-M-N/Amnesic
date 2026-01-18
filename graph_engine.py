import os
import json
import sqlite3
from typing import Annotated, Literal, TypedDict, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_ollama import ChatOllama
from fastembed import TextEmbedding
import numpy as np

# --- 1. THE STATE ---
class AgentState(TypedDict):
    # Immutable
    target_path: str
    goal: str
    
    # Mutable / Persistent
    history: List[str]
    active_files: List[str]    # Semantic Search Results
    current_context: str       # Content loaded in workbench
    manager_decision: dict     # Last decision
    drift_score: float         # Last governance score

# --- 2. THE NODES ---

def node_memory(state: AgentState):
    """
    [MEMORY LAYER]
    Uses FastEmbed to scan the codebase and find files relevant to the goal.
    This runs on every loop to ensure the context stays fresh as the goal evolves.
    """
    print(f"\n--- [MEMORY] Scanning '{state['target_path']}' ---")
    embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    
    # 1. Recursive Scan (In production, this index should be cached)
    all_files = []
    ignore = {'.git', '__pycache__', 'node_modules', '.gemini', '.env'}
    for root, dirs, files in os.walk(state['target_path']):
        dirs[:] = [d for d in dirs if d not in ignore]
        for f in files:
            if f.endswith(('.py', '.md', '.json', '.txt')):
                all_files.append(os.path.relpath(os.path.join(root, f), state['target_path']))
    
    if not all_files:
        print("!! NO FILES FOUND !!")
        return {"active_files": []}

    # 2. Semantic Search
    # We combine the Goal + Last History item to find what's relevant NOW.
    query = state['goal']
    if state['history']:
        query += f" {state['history'][-1]}"
        
    query_vec = list(embedder.embed([query]))[0]
    file_vecs = list(embedder.embed(all_files))
    
    scores = [np.dot(query_vec, f_vec) for f_vec in file_vecs]
    ranked = sorted(zip(scores, all_files), key=lambda x: x[0], reverse=True)
    
    # Top 5 files only to save context window
    top_files = [f for _, f in ranked[:5]]
    print(f"Relevant Files: {top_files}")
    
    return {"active_files": top_files}

def node_manager(state: AgentState):
    """
    [BRAIN LAYER]
    Uses Ollama (Qwen-7B) to decide the next action.
    """
    print("\n--- [MANAGER] Deliberating ---")
    llm = ChatOllama(model="rnj-1:latest", temperature=0.1, format="json")
    
    file_list = "\n".join([f"- {f}" for f in state['active_files']])
    
    prompt = f"""
    SYSTEM: You are the Project Manager.
    GOAL: {state['goal']}
    
    CONTEXT:
    {state['current_context']}
    
    RELEVANT FILES:
    {file_list}
    
    INSTRUCTIONS:
    - If you need to read a file to understand the code, output "retrieve".
    - If you have read the code and are ready to finish, output "done".
    - Do NOT output "code" yet, we are analyzing. 
    
    Output JSON: {{ "action": "retrieve" | "done", "target": "filename", "reasoning": "short text" }}
    """
    
    try:
        response = llm.invoke(prompt)
        decision = json.loads(response.content)
    except Exception as e:
        print(f"!! Manager Glitch: {e}")
        # Fallback to prevent crash
        decision = {"action": "done", "target": "error", "reasoning": "Model failed to output JSON"}
        
    print(f"Decision: {decision['action']} -> {decision['target']}")
    return {"manager_decision": decision}

def node_auditor(state: AgentState):
    """
    [GOVERNANCE LAYER]
    The Watchdog that prevents hallucination and mission drift.
    """
    print("\n--- [AUDITOR] Reviewing Action ---")
    embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    
    goal_vec = list(embedder.embed([state['goal']]))[0]
    action_desc = f"Action: {state['manager_decision']['action']} on {state['manager_decision']['target']}"
    action_vec = list(embedder.embed([action_desc]))[0]
    
    score = np.dot(goal_vec, action_vec)
    print(f"Drift Score: {score:.4f}")
    return {"drift_score": float(score)}

def node_staging(state: AgentState):
    """
    [TOOL LAYER]
    Executes the 'retrieve' action by reading from disk.
    """
    target = state['manager_decision']['target']
    print(f"\n--- [STAGING] Reading {target} ---")
    
    full_path = os.path.join(state['target_path'], target)
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            content = f.read()
        return {"current_context": f"FILE: {target}\nCONTENT:\n{content[:2000]}..."} # Truncate for 7B model
    else:
        return {"current_context": f"ERROR: File {target} not found."}

# --- 3. THE EDGES ---

def edge_router(state: AgentState) -> Literal["staging", "__end__"]:
    score = state['drift_score']
    action = state['manager_decision']['action']
    
    # 1. Governance Check
    if score < 0.35: # Stricter threshold
        print("⛔ AUDITOR BLOCK: Action Drifted.")
        return "__end__"
    
    # 2. Logic Routing
    if action == "retrieve":
        return "staging"
    elif action == "done":
        print("✅ MISSION COMPLETE")
        return "__end__"
        
    return "__end__"

# --- 4. THE GRAPH ---
workflow = StateGraph(AgentState)

workflow.add_node("memory", node_memory)
workflow.add_node("manager", node_manager)
workflow.add_node("auditor", node_auditor)
workflow.add_node("staging", node_staging)

# The Flow: Memory -> Manager -> Auditor -> (Staging or End)
workflow.set_entry_point("memory")
workflow.add_edge("memory", "manager")
workflow.add_edge("manager", "auditor")

workflow.add_conditional_edges(
    "auditor",
    edge_router,
    {
        "staging": "staging",
        "__end__": END
    }
)

# Loop back: Staging -> Memory (To refresh relevant files based on new context)
workflow.add_edge("staging", "memory")

# --- 5. PERSISTENCE ---
# This is what makes it "Amnesic" - it can forget and remember.
db_path = "amnesic_state.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
checkpointer = SqliteSaver(conn)

app = workflow.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    import argparse
    
    # CLI Interface
    parser = argparse.ArgumentParser(description="Amnesic: Persistent Autonomous Agent")
    parser.add_argument("--goal", type=str, default="Analyze the project structure", help="The mission")
    parser.add_argument("--thread", type=str, default="1", help="Thread ID for persistence")
    parser.add_argument("--reset", action="store_true", help="Clear previous state")
    args = parser.parse_args()

    # Config for Persistence
    thread_id = {"configurable": {"thread_id": args.thread}}
    
    print(f"--- AMNESIC ENGINE (Thread: {args.thread}) ---")
    
    # Check for existing state
    current_state = app.get_state(thread_id)
    if current_state.values and not args.reset:
        print("RESUMING from saved state...")
        initial_state = None
    else:
        print("STARTING new mission...")
        initial_state = {
            "target_path": os.getcwd(),
            "goal": args.goal,
            "history": [],
            "active_files": [],
            "current_context": "None",
            "manager_decision": {},
            "drift_score": 0.0
        }

    # Run
    try:
        # If resuming, pass None as input. LangGraph pulls from DB.
        app.invoke(initial_state, config=thread_id)
    except Exception as e:
        print(f"\nStopped: {e}")
        print("(This usually means the mission completed or hit recursion limit)")
