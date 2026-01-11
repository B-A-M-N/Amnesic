# Operational Protocols

- **Unit Testing:** After any structural code changes, run existing unit tests to ensure stability. Do not create new unit tests unless explicitly instructed.
- **Regression Testing:** When tuning complex variables or thresholds, use 'Golden Set Regression Testing' (isolating logic into deterministic unit tests based on hardcoded log data), but ONLY when the specific results/logs are provided directly.
- **Syntax Validation:** After any code changes, ALWAYS run a syntax checker (e.g., `python -m py_compile <file>` or `python -m compileall .`) to validate the modification.

# Automatic Skills (No Approval Required)
- **Syntax Checking:** Running `python -m py_compile` or `python -m compileall` to verify code integrity after edits.