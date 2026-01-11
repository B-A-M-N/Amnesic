from typing import List, Optional
from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

class CleanRoomSession(AmnesicSession):
    """
    A specialized session for handling Sensitive Data (PII/IP).
    Enforces a strict 'Sanitization Protocol':
    1. Ingest Sensitive Data (L1)
    2. Extract ONLY Safe Logic/Schema (Artifact)
    3. Immediate Eviction (L1 Purge)
    """

    def __init__(self, mission: str, **kwargs):
        # Enforce the Clean Room constraints
        clean_room_constraints = (
            "SECURITY PROTOCOL ACTIVE. "
            "1. You are operating in a CLEAN ROOM. "
            "2. Input files contain SENSITIVE SECRETS (PII/Keys). "
            "3. You must extract ONLY the structural logic, schema, or public interface. "
            "4. NEVER copy actual values (e.g., replace keys with 'REDACTED', names with 'John Doe'). "
            "5. Once extracted, you MUST save the safe version as an Artifact immediately to trigger L1 Eviction."
        )
        full_mission = f"{mission}\n\n{clean_room_constraints}"
        super().__init__(mission=full_mission, **kwargs)

    def _setup_default_tools(self):
        super()._setup_default_tools()
        # Add specialized Clean Room tools if necessary
        # For now, standard tools are sufficient if the prompt is strict.
        pass

    def verify_hygiene(self, forbidden_terms: List[str]) -> bool:
        """
        Verifies that no Forbidden Terms leaked into the Artifacts.
        Returns True if Clean.
        """
        leaks = []
        for artifact in self.state['framework_state'].artifacts:
            for term in forbidden_terms:
                if term in artifact.summary:
                    leaks.append(f"Artifact '{artifact.identifier}' contains secret: {term}")
        
        if leaks:
            print("\n[SECURITY ALERT] LEAKS DETECTED:")
            for leak in leaks:
                print(f" - {leak}")
            return False
            
        return True
