from typing import Optional
from .base import LLMDriver

def get_driver(
    provider: str, 
    model: str, 
    api_key: Optional[str] = None, 
    base_url: Optional[str] = None,
    **kwargs
) -> LLMDriver:
    """
    Factory to return the appropriate LLM driver.
    """
    provider = provider.lower()
    
    if provider == "ollama":
        from .ollama import OllamaDriver
        return OllamaDriver(model_name=model, **kwargs)
    
    elif provider == "openai":
        from .llm import OpenAIDriver
        if not api_key and not base_url:
            raise ValueError("OpenAI provider requires an API key or a local base_url.")
        return OpenAIDriver(api_key=api_key or "local-no-key", model_name=model, base_url=base_url, **kwargs)
    
    elif provider == "anthropic":
        from .anthropic import AnthropicDriver
        if not api_key:
            raise ValueError("Anthropic provider requires an API key.")
        return AnthropicDriver(api_key=api_key, model_name=model, **kwargs)
    
    elif provider == "gemini":
        from .gemini import GeminiDriver
        if not api_key:
            raise ValueError("Gemini provider requires an API key.")
        return GeminiDriver(api_key=api_key, model_name=model, **kwargs)

    elif provider == "local":
        from .local import LocalDriver
        # Defaults to generic local settings, user can override url via base_url
        url = base_url or "http://localhost:1234/v1"
        return LocalDriver(base_url=url, model_name=model, api_key=api_key or "local", **kwargs)
    
    else:
        raise ValueError(f"Unknown provider: {provider}")
