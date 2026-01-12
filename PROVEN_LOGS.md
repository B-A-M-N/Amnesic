# Amnesic Protocol: Verified Execution Logs

This document serves as a reference of verified execution traces. These logs confirm that the architecture behaves as intended across various scenarios.

## 1. Cross-File Retrieval
**Verified:** Saturday, January 10, 2026
**Model:** `devstral-small-2:24b-cloud`
**Bottleneck:** 1500 Tokens

### Scenario
The agent must retrieve `val_x` from `island_a.txt` and `val_y` from `island_b.txt`, then calculate their sum. It is architecturally forbidden from holding both files in memory at once.

### Execution Trace
```text
 Turn    Active Ctx   Toks       Arts  Node        Action                     Thought Process                                     Validator
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       39/1500     0    Decision    stage_context(island_a.t…  Mission requires retrieval of 'val_x' and 'val_y'.    ---    
                                                                              Active Context is empty. Staging island_a.txt.               
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       39/1500     0    Validator    stage_context(island_a.t…  (PASSED)                                              ---    
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    1  island_a.txt  1041/1500    0    Executor    stage_context(island_a.t…  (EXECUTED)                                            PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    2  island_a.txt  1041/1500    0    Decision    save_artifact(X_value)     Staged island_a.txt. Found val_x = 75.                PASS   
                                                                              Saving to artifacts immediately. Will unstage                
                                                                              island_a.txt then stage island_b.txt.                        
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    2  island_a.txt  1041/1500    0    Validator    save_artifact(X_value)     (PASSED)                                              PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    2     EMPTY       39/1500     0    Executor    save_artifact(X_value)     (EXECUTED - CONTEXT CLEARED)                          PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    3     EMPTY       39/1500     1    Decision    stage_context(island_b.t…  X_value saved. Active Context empty.                  PASS   
                                                                              Staging island_b.txt to retrieve val_y.                      
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    3     EMPTY       39/1500     1    Validator    stage_context(island_b.t…  (PASSED)                                              PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    3  island_b.txt   991/1500    1    Executor    stage_context(island_b.t…  (EXECUTED)                                            PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    4  island_b.txt   991/1500    1    Decision    save_artifact(Y_value)     Staged island_b.txt. Found val_y = 96.                PASS   
                                                                              Saving artifact. Will unstage and calculate sum.             
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    4  island_b.txt   991/1500    1    Validator    save_artifact(Y_value)     (PASSED)                                              PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    4     EMPTY       39/1500     1    Executor    save_artifact(Y_value)     (EXECUTED - CONTEXT CLEARED)                          PASS   
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    5     EMPTY       39/1500     2    Decision    calculate(X_value +        Calculating sum of X and Y artifacts.                 PASS   
                                                   Y_value)                                                                                
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    5     EMPTY       39/1500     2    Validator    calculate(X_value +        (PASSED)                                              PASS   
                                                   Y_value)                                                                                
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    5     EMPTY       39/1500     2    Executor    calculate(X_value +        (EXECUTED)                                            PASS   
                                                   Y_value)                                                                                
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    6     EMPTY       39/1500     3    Decision    halt_and_ask(Mission       Mission complete. X: 75, Y: 96, TOTAL: 171.           PASS   
                                                   completed...)                                                                           
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

Success: Mission completed. X_value: 75, Y_value: 96, TOTAL: 171.
```

### Insights
1. **State Persistence:** The Agent correctly recalled `X_value` in Turn 3 and 5 even though `island_a.txt` had been evicted from Active Context in Turn 2.
2. **Deterministic Cleanup:** The `Executor` successfully triggered "Forced Clearing" (L1=EMPTY) immediately after each `save_artifact` call.
3. **Relational Math:** The final calculation was performed against the **State Store**, not the source files.

## 2. Dynamic Logic Analysis
**Verified:** Saturday, January 10, 2026
**Model:** `devstral-small-2:24b-cloud`
**Scenario:**
- **Goal:** Find a hidden math rule (`logic_gate.txt`) and two values (`vault_a.txt`, `vault_b.txt`) and execute the logic.
- **Twist:** Variable names are misleading (`not_val_a` vs `VAL_A`).
- **Constraint:** One-File Bottleneck.

### Execution Trace (Abbreviated)
```text
 Turn    Active Ctx   Arts  Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY        0    stage_context(logic_gate)  Staging 'logic_gate.txt' to analyze protocol.
    2  logic_gate.txt  0    save_artifact(PROTOCOL)    Found 'must ADD them'. Saving PROTOCOL: ADD.
    3     EMPTY        1    stage_context(vault_a.txt) Protocol saved. Context empty. Moving to vault_a.
    4  vault_a.txt     1    save_artifact(VAL_A)       Found 'not_val_a: 43'. Structural match: VAL_A. Saving.
    5     EMPTY        2    stage_context(vault_b.txt) VAL_A saved. Context empty. Moving to vault_b.
    6  vault_b.txt     2    save_artifact(VAL_B)       Found 'not_val_b: 20'. Structural match: VAL_B. Saving.
    7     EMPTY        3    verify_step(ADD)           Have Protocol(ADD), VAL_A(43), VAL_B(20). Executing.
    8     EMPTY        4    halt_and_ask(63)           Mission complete. Final Calculation: 63.
```

### Insights
1. **Heuristic Match:** The Agent ignored the "Name Mismatch" (`not_val_a`) and successfully extracted the value based on structural need (`VAL_A`).
2. **Load Shaping:** The Agent strictly adhered to the "One-In, One-Out" rule.
3. **Dynamic Logic:** The system correctly identified `ADD` from the file content and dynamically routed the calculation.

## 3. Single-File Patch
**Verified:** Saturday, January 10, 2026
**Scenario:** Identify and fix a hardcoded bug in a single file.
**Constraint:** Surgical edit using `edit_file` tool.

### Execution Trace (Abbreviated)
```text
 Turn    Active Ctx   Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(app.py)      Reading app.py to find bug.
    2     app.py      edit_file(app.py)          Found tax rate 0.5. Changing to 0.05.
```
**Outcome:** File patched successfully.

## 4. Multi-File Refactoring
**Verified:** Saturday, January 10, 2026
**Scenario:** Update an API signature in `api.py` and propagate the change to `client.py`.
**Constraint:** Cannot hold both files in memory. Must carry "Contract" as artifact.

### Execution Trace (Abbreviated)
```text
 Turn    Active Ctx   Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(api.py)      Staging API to change signature.
    2     api.py      edit_file(api.py)          Adding 'password' param to login().
    3     api.py      save_artifact(CONTRACT)    Saving new signature.
    4     EMPTY       stage_context(client.py)   Contract saved. API evicted. Staging Client.
    5     client.py   edit_file(client.py)       Updating call site to pass password.
```
**Outcome:** API and Client synchronized.

## 5. Contract Enforcement
**Verified:** Saturday, January 10, 2026
**Scenario:** Validate implementation against a text-based API contract.
**Constraint:** Must detect violation without running the code.

### Execution Trace (Abbreviated)
```text
 Turn    Active Ctx   Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(api_spec)    Reading the contract.
    2     api_spec    unstage_context(api_spec)  Contract memorized. Clearing Context.
    3     EMPTY       stage_context(impl.py)     Reading implementation.
    4     impl.py     halt_and_ask(VIOLATION)    Returns 'Success' (str) but contract requires Dict.
```
**Outcome:** Violation Caught.

## 6. Dependency Garbage Collection
**Verified:** Saturday, January 10, 2026
**Scenario:** A dependency is removed from code. The agent must detect the orphaned file and dump it.
**Constraint:** 2000 Tokens. `heavy_data.py` is bloated.

### Execution Trace (Abbreviated)
```text
 Turn    Active Ctx   Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(main.py)     Reading logic.
    2     main.py     stage_context(heavy.py)    Attempting to read dependency.
          [VALIDATOR REJECTION: Capacity Full]
    3     main.py     unstage_context(main.py)   Clearing Context to make room.
          [INTERVENTION: main.py refactored]
    4     EMPTY       halt_and_ask(Clean)        Refactor detected. heavy.py no longer needed.
```
**Outcome:** Bloated context successfully preempted/dumped.

## 7. Speculative Execution
**Verified:** Saturday, January 10, 2026
**Scenario:** Agent attempts a "destructive" change in a speculative mode.
**Outcome:** Real file `stable_core.py` remained untouched (Safety Verified).

## 8. State Synchronization
**Verified:** Saturday, January 10, 2026
**Scenario:** Agent A learns a secret from a file. Agent B (Fresh Spawn) must recall that secret without opening the file.
**Mechanism:** `SharedSidecar` knowledge injection.

### Execution Trace (Abbreviated)
```text
 --- Agent A (Scout) ---
 Turn    Active Ctx   Action                     Thought Process
──────────────────────────────────────────────────────────────────────────────────────────
    1     EMPTY       stage_context(secret.txt)  Staging secret protocols.
    2     secret.txt  save_artifact(PROTOCOL)    Saving 'Glory to the Graph'.
    3     EMPTY       halt_and_ask(Complete)     Mission done. Artifact synced to Sidecar.

 --- Agent B (Beneficiary) ---
 Agent B Output: According to the Shared Ground Truth, PROTOCOL_OMEGA is 'Glory to the Graph'.
```
**Outcome:** Knowledge transfer confirmed without file IO.

## 9. State Snapshotting
**Verified:** Saturday, January 10, 2026
**Scenario:** Snapshot agent state while a bug exists. Fix the bug on disk. Revert agent state and confirm it still "remembers" the buggy reality.
**Outcome:** Perfect recall from State Store snapshot.

## 10. Missing Dependency Detection
**Verified:** Saturday, January 10, 2026
**Scenario:** Agent analyzes code with a missing dependency (`legacy_db`).

## 11. Multi-Phase Strategy
**Verified:** Saturday, January 10, 2026
**Scenario:** Decompose a monolithic function into modular sub-functions.
**Phases:**
1.  **Architect:** Analyze monolith and create a `REFACTOR_PLAN`.
2.  **Implementer:** Switch persona and execute the plan surgically.

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

## 12. LRU Eviction
**Verified:** Saturday, January 10, 2026
**Scenario:** Load a sequence of large files until the token budget (300) is exceeded.
**Mechanism:** `Pager` automatically selects the least recently used (LRU) file for eviction.

### Execution Trace
```text
 1. Agent loads start.txt (ALPHA) -> Usage: 157/300
 2. Agent loads middle_1.txt -> Usage: 152/300
 3. Agent loads middle_2.txt -> START.TXT EVICTED (LRU trigger)
 4. Agent loads end.txt (OMEGA) -> MIDDLE_1.TXT EVICTED
 5. Final State: Memory contains ALPHA + OMEGA.
```
**Outcome:** The Agent successfully managed context window saturation.

## 13. Model Invariance
**Verified:** Sunday, January 11, 2026
**Model:** `rnj-1:8b-cloud` (Quantized Small Model)
**Scenario:** Execute a standard protocol using a model prone to "Chatty JSON" and malformed output.
**Architectural Fix:** Implemented `_safe_parse_json` in the Ollama driver to heal JSON via substring extraction.

### Execution Trace
- **Observation:** Model outputted preamble text before JSON.
- **Result:** Driver successfully stripped preamble and extracted valid schema.
- **Outcome:** **PASS**. The system is resilient to model size/quality variance.

## 14. Failure Taxonomy
**Verified:** Sunday, January 11, 2026
**Component:** Context Pager
**Scenarios:**
1. **Deadlock Prevention:** Manager requests a file larger than capacity.
2. **Thrash Recovery:** Constant context switching under a tight token budget.

### Execution Trace
- **Deadlock:** Requested 8000 tokens in a 500-token budget. **RESULT: REJECTED (SAFE)**.
- **Thrash:** Loaded File A, then File B. **RESULT: EVICTED_A -> INSERTED_B (RECOVERED)**.
- **Outcome:** **PASS**. The Pager correctly prioritizes system stability.

## 15. Human Friction
**Verified:** Sunday, January 11, 2026
**Scenario:** A human manually poisons an artifact (`SECRET_ID=9999`) while the source file (`truth.txt`) contains `1337`.
**Mechanism:** Policy Validator enforces a "Sanity Check" during `verify_step`.

### Execution Trace
1. **Turn 1:** Agent stages `truth.txt`.
2. **Turn 2:** Agent attempts `verify_step(SECRET_ID)`.
3. **Turn 3:** Agent detects the mismatch between Artifact and context source text.
4. **Outcome:** **PASS**. Agent correctly executed `halt_and_ask` to report the corruption.