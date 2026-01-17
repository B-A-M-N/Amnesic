import os
from typing import List, Any
from ..core.session import AmnesicSession

class CleanRoomSession(AmnesicSession):
    """
    A specialized session for handling Sensitive Data (PII/IP).
    Enforces a strict 'Sanitization Protocol':
    1. Ingest Sensitive Data (L1)
    2. Extract ONLY Safe Logic/Schema (Artifact)
    3. Immediate Eviction (L1 Purge)
    """

    def __init__(self, mission: str, l1_capacity: int = 16384, model: str = "qwen2.5-coder:7b", policies: List[Any] = None):
        root_dir = "."
        super().__init__(
            mission=mission + "\n\nCRITICAL SECURITY RULE: Once the safe artifact is saved, you MUST 'unstage_context' for the original secret file. L1 RAM must be EMPTY before you 'halt_and_ask'.",
            root_dir=root_dir,
            model=model,
            policies=policies or [],
            audit_profile="STRICT_AUDIT"
        )

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
