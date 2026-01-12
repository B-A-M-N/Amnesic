from .llm import OpenAIDriver

class LocalDriver(OpenAIDriver):
    """
    A driver for local OpenAI-compatible endpoints (e.g., LM Studio, LocalAI, vLLM, Llama.cpp server).
    Defaults to localhost:1234 but can be overridden.
    """
    def __init__(self, base_url: str = "http://localhost:1234/v1", model_name: str = "local-model", api_key: str = "not-needed", seed: Optional[int] = None):
        super().__init__(api_key=api_key, model_name=model_name, base_url=base_url, seed=seed)
