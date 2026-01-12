from amnesic.core.session import AmnesicSession
from amnesic.presets.code_agent import Artifact

class DocGeneratorSession(AmnesicSession):
    """
    A specialized session for generating documentation.
    Enforces 'Contextual Documentation':
    1. Ingest Code (L1).
    2. Map dependencies and public interfaces.
    3. Generate Technical Documentation (Markdown).
    4. Ensure docs accurately reflect current state of code.
    """

    def __init__(self, mission: str, **kwargs):
        doc_protocol = (
            "DOCUMENTATION PROTOCOL ACTIVE. "
            "1. You are the TECHNICAL ARCHITECT. "
            "2. Goal: Generate clear, accurate Markdown documentation for the codebase. "
            "3. Focus on: 'Why' things are done, not just 'What'. "
            "4. Requirement: Use Mermaid diagrams for flowcharts if needed. "
            "5. Once docs are written, save them as Artifacts before writing to disk."
        )
        full_mission = f"{mission}\n\n{doc_protocol}"
        super().__init__(mission=full_mission, **kwargs)
        
        # Inject Doc Template
        self.state['framework_state'].artifacts.append(
            Artifact(
                identifier="DOC_TEMPLATE",
                type="config",
                summary="# Module Name\n## Overview\n## API Reference\n## Examples",
                status="verified_invariant"
            )
        )

