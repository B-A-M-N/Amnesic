import json
import logging
from typing import List, Type, Optional, Callable
from pydantic import BaseModel
import openai
from .base import LLMDriver

logger = logging.getLogger("amnesic.driver.openai")

class OpenAIDriver(LLMDriver):
    def __init__(self, api_key: str, model_name: str = "gpt-4o", base_url: Optional[str] = None, temperature: float = 0.7, seed: Optional[int] = None):
        self.model_name = model_name
        self.temperature = temperature
        self.seed = seed
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.last_request_tokens = 0

    def embed(self, text: str) -> List[float]:
        try:
            response = self.client.embeddings.create(input=[text], model="text-embedding-3-small")
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI Embedding failed: {e}")
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        attempt = 0
        while attempt <= retries:
            full_content = ""
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    stream=True,
                    temperature=self.temperature,
                    seed=self.seed,
                    response_format={"type": "json_object"}
                )
                
                for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    full_content += content
                    if stream_callback:
                        stream_callback(content)
                
                return schema.model_validate(json.loads(full_content))
                
            except Exception as e:
                logger.error(f"OpenAI generation failed: {e}")
                attempt += 1
                
        raise RuntimeError(f"OpenAI failed to generate valid {schema.__name__}")

    def generate_raw(self, prompt: str, system_prompt: str) -> str:
        self._update_token_usage(system_prompt, prompt)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature
        )
        return response.choices[0].message.content