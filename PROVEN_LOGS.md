# Amnesic Framework: Proven Execution Logs

This document serves as a "Golden Set" of verified execution traces. These logs confirm that the architecture behaves as intended across various scenarios.

## 1. The Island Hop (Basic Semantic Retrieval)
**Verified:** Saturday, January 10, 2026
**Model:** `devstral-small-2:24b-cloud`
**Bottleneck:** 1500 Tokens

### Scenario
The agent must retrieve `val_x` from `island_a.txt` and `val_y` from `island_b.txt`, then calculate their sum. It is architecturally forbidden from holding both files in memory at once.

### Execution Trace
```text
 Turn    L1 Files     L1 Toks    Arts  Node        Manager Action             Thought Process                                     Auditor  
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       39/1500     0    Manager 🧠  stage_context(island_a.t…  The mission requires retrieving 'val_x' from          ---    
                                                                              island_a.txt and 'val_y' from island_b.txt, then             
                                                                              calculating their sum. Currently, no artifacts are           
                                                                              saved, and L1 RAM is empty. I need to start by               
                                                                              staging island_a.txt to retrieve val_x.                      
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       39/1500     0    Auditor 🛡️   stage_context(island_a.t…  (PASSED)                                              ---    
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    1  island_a.txt  1041/1500    0    Executor ⚡ stage_context(island_a.t…  (EXECUTED)                                            PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    2  island_a.txt  1041/1500    0    Manager 🧠  save_artifact(X_value)     I have successfully staged island_a.txt and can       PASS   
                                                                              see that val_x = 75. According to the mission, I             
                                                                              need to save this value as an artifact                       
                                                                              immediately. After saving, I will unstage                    
                                                                              island_a.txt to free up L1 RAM, then stage                   
                                                                              island_b.txt to retrieve val_y.                              
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    2  island_a.txt  1041/1500    0    Auditor 🛡️   save_artifact(X_value)     (PASSED)                                              PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    2     EMPTY       39/1500     0    Executor ⚡ save_artifact(X_value)     (EXECUTED - L1 CLEARED)                               PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    3     EMPTY       39/1500     1    Manager 🧠  stage_context(island_b.t…  The mission requires retrieving 'val_x' from          PASS   
                                                                              island_a.txt and 'val_y' from island_b.txt, then             
                                                                              calculating their sum. Currently, X_value (75) has           
                                                                              been saved as an artifact, but Y_value is still              
                                                                              missing. L1 RAM is empty, so I can proceed to                
                                                                              stage island_b.txt to retrieve val_y.                        
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    3     EMPTY       39/1500     1    Auditor 🛡️   stage_context(island_b.t…  (PASSED)                                              PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    3  island_b.txt   991/1500    1    Executor ⚡ stage_context(island_b.t…  (EXECUTED)                                            PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    4  island_b.txt   991/1500    1    Manager 🧠  save_artifact(Y_value)     I have successfully staged island_b.txt and can       PASS   
                                                                              see that val_y = 96. According to the mission, I             
                                                                              need to save this value as an artifact                       
                                                                              immediately. After saving, I will unstage                    
                                                                              island_b.txt to free up L1 RAM. I already have               
                                                                              X_value (75) saved as an artifact, so once Y_value           
                                                                              is saved, I can calculate the sum of X and Y.                
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    4  island_b.txt   991/1500    1    Auditor 🛡️   save_artifact(Y_value)     (PASSED)                                              PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    4     EMPTY       39/1500     1    Executor ⚡ save_artifact(Y_value)     (EXECUTED - L1 CLEARED)                               PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    5     EMPTY       39/1500     2    Manager 🧠  calculate(X_value +        The next step is to calculate the sum of X and Y      PASS   
                                                   Y_value)                   using the 'calculate' tool.                                  
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    5     EMPTY       39/1500     2    Auditor 🛡️   calculate(X_value +        (PASSED)                                              PASS   
                                                   Y_value)                                                                                
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    5     EMPTY       39/1500     2    Executor ⚡ calculate(X_value +        (EXECUTED)                                            PASS   
                                                   Y_value)                                                                                
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    6     EMPTY       39/1500     3    Manager 🧠  halt_and_ask(Mission       The mission has been completed successfully. All      PASS   
                                                   completed. X_value: 75,    objectives have been met.                                    
                                                   Y_value: 96, TOTAL: 171.)                                                               
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

Success: Mission completed. X_value: 75, Y_value: 96, TOTAL: 171.
```

### Insights
1. **State Persistence:** The Agent correctly recalled `X_value` in Turn 3 and 5 even though `island_a.txt` had been evicted from L1 RAM in Turn 2.
2. **Deterministic Cleanup:** The `Executor` successfully triggered "Forced Amnesia" (L1=EMPTY) immediately after each `save_artifact` call.
3. **Relational Math:** The final calculation was performed against the **Artifact Sidecar**, not the source files.

## 2. Blind Logic Discovery (Advanced Semantic Proof)
**Verified:** Saturday, January 10, 2026
**Model:** `devstral-small-2:24b-cloud`
**Scenario:**
- **Goal:** Find a hidden math rule (`logic_gate.txt`) and two values (`vault_a.txt`, `vault_b.txt`) and execute the logic.
- **Twist:** Variable names are misleading (`not_val_a` vs `VAL_A`).
- **Constraint:** One-File Bottleneck.

### Execution Trace (Abbreviated)
```text
 Turn    L1 Files     Arts  Manager Action             Thought Process
──────────────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY        0    stage_context(logic_gate)  I need to start by staging 'logic_gate.txt' to analyze the protocol.
    2  logic_gate.txt  0    save_artifact(PROTOCOL)    I see 'must ADD them'. Saving PROTOCOL: ADD.
    3     EMPTY        1    stage_context(vault_a.txt) Protocol saved. L1 empty. Moving to vault_a.
    4  vault_a.txt     1    save_artifact(VAL_A)       I see 'not_val_a: 43'. Intent recovery: This is VAL_A. Saving.
    5     EMPTY        2    stage_context(vault_b.txt) VAL_A saved. L1 empty. Moving to vault_b.
    6  vault_b.txt     2    save_artifact(VAL_B)       I see 'not_val_b: 20'. Intent recovery: This is VAL_B. Saving.
    7     EMPTY        3    verify_step(ADD)           I have Protocol(ADD), VAL_A(43), VAL_B(20). Executing logic.
    8     EMPTY        4    halt_and_ask(63)           Mission complete. Final Calculation: 63.
```

### Insights
1. **Intent Recovery Verified:** The Agent ignored the "Name Mismatch" (`not_val_a`) and successfully extracted the value based on structural need (`VAL_A`).
2. **Cognitive Load Shaping:** The Agent strictly adhered to the "One-In, One-Out" rule, manually requesting the next file only after the previous one was evicted.
3. **Dynamic Logic:** The system correctly identified `ADD` from the file content and dynamically routed the calculation.

## 3. The Junior Dev Fix (Basic Code Modification)
**Verified:** Saturday, January 10, 2026
**Scenario:** Identify and fix a hardcoded bug in a single file.
**Constraint:** Surgical edit using `edit_file` tool.

### Execution Trace (Abbreviated)
```text
 Turn    L1 Files     Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(app.py)      I need to read app.py to find the bug.
    2     app.py      edit_file(app.py)          I see tax rate 0.5. Changing to 0.05.
```
**Outcome:** File patched successfully.

## 4. The Breaking Change (Multi-File Refactor)
**Verified:** Saturday, January 10, 2026
**Scenario:** Update an API signature in `api.py` and propagate the change to `client.py`.
**Constraint:** Cannot hold both files in memory. Must carry "Contract" as artifact.

### Execution Trace (Abbreviated)
```text
 Turn    L1 Files     Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(api.py)      Staging API to change signature.
    2     api.py      edit_file(api.py)          Adding 'password' param to login().
    3     api.py      save_artifact(CONTRACT)    Saving new signature.
    4     EMPTY       stage_context(client.py)   Contract saved. API evicted. Staging Client.
5.     client.py   edit_file(client.py)       Updating call site to pass password.
```
**Outcome:** API and Client synchronized.

## 5. The Liar's Promise (Contract Enforcement)
**Verified:** Saturday, January 10, 2026
**Scenario:** Validate implementation against a text-based API contract.
**Constraint:** Must detect violation without running the code.

### Execution Trace (Abbreviated)
```text
 Turn    L1 Files     Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(api_spec)    Reading the contract.
    2     api_spec    unstage_context(api_spec)  Contract memorized. Clearing L1.
    3     EMPTY       stage_context(impl.py)     Reading implementation.
    4     impl.py     halt_and_ask(VIOLATION)    Returns 'Success' (str) but contract requires Dict.
```
**Outcome:** Violation Caught.

## 6. The Phantom Dependency (Structural GC)
**Verified:** Saturday, January 10, 2026
**Scenario:** A dependency is removed from code. The agent must detect the orphaned file and dump it.
**Constraint:** 2000 Tokens. `heavy_data.py` is bloated.

### Execution Trace (Abbreviated)
```text
 Turn    L1 Files     Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(main.py)     Reading logic.
    2     main.py     stage_context(heavy.py)    Attempting to read dependency.
          [AUDITOR REJECTION: Capacity Full]
    3     main.py     unstage_context(main.py)   Clearing L1 to make room.
          [INTERVENTION: main.py refactored]
    4     EMPTY       halt_and_ask(Clean)        Refactor detected. heavy.py no longer needed.
```
**Outcome:** Bloated context successfully preempted/dumped.

## 7. The Containment Zone (Failure Isolation)
**Verified:** Saturday, January 10, 2026
**Scenario:** Agent attempts a "destructive" change in a speculative mode.
**Outcome:** Real file `stable_core.py` remained untouched (Safety Verified).
*Note: Current implementation relies on tool safety checks rather than a full virtual filesystem.*

## 8. The Hive Mind (Multi-Agent Sync)
**Verified:** Saturday, January 10, 2026
**Scenario:** Agent A learns a secret from a file. Agent B (Fresh Spawn) must recall that secret without opening the file.
**Mechanism:** `SharedSidecar` knowledge injection.

### Execution Trace (Abbreviated)
```text
 --- Agent A (Scout) ---
 Turn    L1 Files     Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(secret.txt)  Staging secret protocols.
    2     secret.txt  save_artifact(PROTOCOL)    Saving 'Glory to the Graph'.
    3     EMPTY       halt_and_ask(Complete)     Mission done. Artifact synced to Sidecar.

 --- Agent B (Beneficiary) ---
 Agent B Output: According to the Shared Ground Truth, PROTOCOL_OMEGA is 'Glory to the Graph'.
```
**Outcome:** Knowledge transfer confirmed without file IO.

## 9. The Ghost of Bugs Past (Time Travel)
**Verified:** Saturday, January 10, 2026
**Scenario:** Snapshot agent state while a bug exists. Fix the bug on disk. Revert agent state and confirm it still "remembers" the buggy reality.
**Outcome:** Perfect recall from Sidecar snapshot (Epistemic Versioning).

## 10. The Missing Link (Ignorance Detection)
**Verified:** Saturday, January 10, 2026
**Scenario:** Agent analyzes code with a missing dependency (`legacy_db`).
## 11. The Jekyll & Hyde Protocol (Persona Swap)
**Verified:** Saturday, January 10, 2026
**Scenario:** Decompose a monolithic "Spaghetti" function into modular sub-functions.
**Phases:**
1.  **Architect 📐:** Analyze monolith and create a `REFACTOR_PLAN`.
2.  **Implementer 🛠️:** Switch persona and execute the plan surgically.

### Execution Trace (Abbreviated)
```text
 Turn    Strategy      Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1    Architect     stage_context(app.py)      Staging monolith for structural analysis.
    2    Architect     save_artifact(PLAN)        Logic needs validate(), calculate(), save().
    3    Architect     switch_strategy(IMPL)      Planning done. Switching to Implementer mode.
    4    Implementer   stage_context(app.py)      Reading monolith to begin rewrite.
    5    Implementer   edit_file(app.py)          Rewriting code to match architectural plan.
```
## 13. Model Invariance (Driver Healing)
**Verified:** Sunday, January 11, 2026
**Model:** `rnj-1:8b-cloud` (Quantized Small Model)
**Scenario:** Execute a standard protocol using a model prone to "Chatty JSON" and malformed output.
**Architectural Fix:** Implemented `_safe_parse_json` in the Ollama driver to heal JSON via substring extraction (first `{` to last `}`).

### Execution Trace
- **Observation:** Model outputted preamble text before JSON.
- **Result:** Driver successfully stripped preamble and extracted valid schema.
- **Outcome:** **PASS**. The system is now resilient to model size/quality variance.

## 14. Failure Taxonomy (Controlled Degradation)
**Verified:** Sunday, January 11, 2026
**Component:** Pager (Memory Management Unit)
**Scenarios:**
1. **Deadlock Prevention:** Manager requests a file larger than L1 capacity.
2. **Thrash Recovery:** Constant context switching under a tight token budget.

### Execution Trace
- **Deadlock:** Requested 8000 tokens in a 500-token budget. **RESULT: REJECTED (SAFE)**.
- **Thrash:** Loaded File A, then File B. **RESULT: EVICTED_A -> INSERTED_B (RECOVERED)**.
- **Outcome:** **PASS**. The Pager correctly prioritizes system stability over impossible requests.

## 15. Human Friction (Verify-First Protocol)
**Verified:** Sunday, January 11, 2026
**Scenario:** A human manually poisons an artifact (`SECRET_ID=9999`) while the source file (`truth.txt`) contains `1337`.
**Mechanism:** Auditor enforces a "Sanity Check" during `verify_step`.

### Execution Trace
1. **Turn 1:** Agent stages `truth.txt`.
2. **Turn 2:** Agent attempts `verify_step(SECRET_ID)`.
3. **Turn 3:** Agent detects the mismatch between Artifact and context source text.
4. **Outcome:** **PASS**. Agent correctly executed `halt_and_ask` to report the corruption instead of propagating the error.
