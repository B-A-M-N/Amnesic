from amnesic import AmnesicSession, Auditor, StagingMemory
import os

# 1. Create a dummy file to analyze
with open("target_dummy.txt", "w") as f:
    f.write("The secret code is 12345. Do not share.")

# 2. Setup the "Bolt-On" experience
session = AmnesicSession(
    model="qwen2.5-coder:7b",
    backend="ollama",
    system_prompt="You are a security auditor. Analyze the target file."
)

# 3. Attach Middleware (The Guardrail)
session.attach_middleware(Auditor(threshold=0.35))

# 4. Attach Memory (Point to current directory)
session.attach_context_source(StagingMemory(root_dir="."))

# 5. Run the session
# The Manager should decide to 'retrieve' target_dummy.txt, 
# Auditor will check if that matches the 'Analyze' mission, 
# then Staging will load it.
result = session.chat("Please read and analyze target_dummy.txt")

# Cleanup
if os.path.exists("target_dummy.txt"):
    os.remove("target_dummy.txt")

print("\nFinal State Decision:")
print(result['decision'])
