import json
import logging
import os
from typing import List, Type, Optional, Callable
from pydantic import BaseModel
from .base import LLMDriver

logger = logging.getLogger("amnesic.driver.gemini")

class GeminiDriver(LLMDriver):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro-latest", seed: Optional[int] = None):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Gemini driver requires 'google-generativeai' package.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.seed = seed
        self.last_request_tokens = 0

    def embed(self, text: str) -> List[float]:
        try:
            import google.generativeai as genai
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
                title="Embedding"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Gemini embedding failed: {e}")
            return []

    def generate_structured(self, user_prompt: str, schema: Type[BaseModel], system_prompt: str, retries: int = 2) -> BaseModel:
        return self.generate_structured_with_stream(user_prompt, schema, system_prompt, None, retries)

    def generate_structured_with_stream(
        self, 
        user_prompt: str, 
        schema: Type[BaseModel], 
        system_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        retries: int = 2
    ) -> BaseModel:
        self._update_token_usage(system_prompt, user_prompt)
        
        import google.generativeai as genai
        
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            seed=self.seed
        )

        chat = self.model.start_chat(history=[
            {"role": "user", "parts": [system_prompt]}
        ])

        attempt = 0
        while attempt <= retries:
            try:
                # Gemini doesn't support streaming with structured output (JSON mode) perfectly in all SDK versions yet,
                # but we can try. If streaming is required, we might need raw generation.
                # For now, we'll stream but accumulate for the final parse.
                
                response = chat.send_message(user_prompt, generation_config=generation_config, stream=True)
                
                full_content = ""
                for chunk in response:
                    if chunk.text:
                        full_content += chunk.text
                        if stream_callback:
                            stream_callback(chunk.text)
                
                return schema.model_validate(json.loads(full_content))

            except Exception as e:
                logger.error(f"Gemini generation failed: {e}")
                attempt += 1
        
        raise RuntimeError(f"Gemini failed to generate valid {schema.__name__}")

    def generate_raw(self, prompt: str, system_prompt: str) -> str:
        self._update_token_usage(system_prompt, prompt)
        chat = self.model.start_chat(history=[
             {"role": "user", "parts": [system_prompt]}
        ])
        response = chat.send_message(prompt)
        return response.text
