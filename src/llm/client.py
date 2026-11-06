import re
import time
from typing import Any

from src.config import get_api_key


class LLMClient:
    def generate(self, system: str, user: str) -> str:
        raise NotImplementedError


class ProviderClient(LLMClient):
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.provider = cfg["llm"]["provider"].lower()
        self.model = cfg["llm"]["model"]
        self.temperature = cfg["llm"]["temperature"]
        self.timeout = cfg["llm"]["timeout_seconds"]
        self.client = None

    def _create_client(self):
        if self.provider == "groq":
            from groq import Groq

            return Groq(api_key=get_api_key("groq"), timeout=self.timeout)
        if self.provider == "gemini":
            import google.generativeai as genai

            genai.configure(api_key=get_api_key("gemini"))
            return genai.GenerativeModel(self.model)
        if self.provider == "openai":
            from openai import OpenAI

            return OpenAI(api_key=get_api_key("openai"), timeout=self.timeout)
        if self.provider == "anthropic":
            from anthropic import Anthropic

            return Anthropic(api_key=get_api_key("anthropic"), timeout=self.timeout)
        if self.provider == "openrouter":
            from openai import OpenAI

            return OpenAI(
                api_key=get_api_key("openrouter"),
                base_url="https://openrouter.ai/api/v1",
                timeout=self.timeout,
                default_headers={"X-Title": "HDFC Mutual Fund FAQ"},
            )
        raise ValueError(f"Unknown LLM provider: {self.provider}")

    def _get_client(self):
        if self.client is None:
            self.client = self._create_client()
        return self.client

    def _request(self, system: str, user: str) -> str:
        client = self._get_client()
        if self.provider in {"groq", "openai", "openrouter"}:
            request_options = {
                "model": self.model,
                "temperature": self.temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            if self.provider == "openrouter":
                request_options["max_tokens"] = 400
            response = client.chat.completions.create(**request_options)
            return response.choices[0].message.content or ""
        if self.provider == "gemini":
            response = client.generate_content(
                f"{system}\n\n{user}",
                generation_config={"temperature": self.temperature},
            )
            return response.text or ""
        if self.provider == "anthropic":
            response = client.messages.create(
                model=self.model,
                max_tokens=400,
                temperature=self.temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
        raise ValueError(f"Unknown LLM provider: {self.provider}")

    def generate(self, system: str, user: str) -> str:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                answer = self._request(system, user)
                return re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1)
        raise RuntimeError(f"{self.provider} answer generation failed") from last_error


def get_client(cfg: dict[str, Any]) -> LLMClient:
    return ProviderClient(cfg)
