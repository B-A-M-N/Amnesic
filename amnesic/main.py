import argparse
from amnesic.app import FrameworkApp

def main():
    parser = argparse.ArgumentParser(description="Amnesic Framework: Kernel Scaffolding")
    parser.add_argument("mission", type=str, help="The goal/mission for the agent")
    parser.add_argument("--root", type=str, default="./", help="Root directory")
    parser.add_argument("--model", type=str, default="qwen2.5-coder:7b", help="Model name")
    parser.add_argument("--provider", type=str, default="ollama", help="LLM Provider (ollama, openai, anthropic, gemini, local)")
    parser.add_argument("--turns", type=int, default=15, help="Max turns")
    parser.add_argument("--hybrid", action="store_true", help="Enable Hybrid Search")
    
    args = parser.parse_args()
    
    app = FrameworkApp(
        mission=args.mission, 
        root_dir=args.root, 
        model=args.model,
        provider=args.provider,
        use_hybrid=args.hybrid
    )
    
    app.run(max_turns=args.turns)

if __name__ == "__main__":
    main()
