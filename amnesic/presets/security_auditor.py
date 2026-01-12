from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

class SecurityAuditorSession(AmnesicSession):
    """
    A specialized session for identifying and fixing vulnerabilities.
    Enforces 'Security-First Reasoning':
    1. Scan Source for common patterns (SQLi, XSS, Hardcoded Keys).
    2. Log vulnerabilities as individual Artifacts.
    3. Suggest surgically precise fixes.
    """

    def __init__(self, mission: str, **kwargs):
        security_protocol = (
            "SECURITY AUDIT PROTOCOL ACTIVE. "
            "1. You are the SENIOR SECURITY AUDITOR. "
            "2. Search for: Hardcoded secrets, SQL injection, insecure deserialization, and weak crypto. "
            "3. For every finding, you MUST save an Artifact named 'VULN:<name>' with the location and description. "
            "4. Suggest a fix for each finding using 'edit_file'. "
            "5. Prioritize high-severity issues (remote code execution) over low-severity (best practices)."
        )
        full_mission = f"{mission}\n\n{security_protocol}"
        super().__init__(mission=full_mission, **kwargs)
        
        # Inject Vulnerability Checklist
        self.state['framework_state'].artifacts.append(
            Artifact(
                identifier="OWASP_CHECKLIST",
                type="config",
                summary="Check for: 1. Broken Access Control, 2. Cryptographic Failures, 3. Injection.",
                status="verified_invariant"
            )
        )

