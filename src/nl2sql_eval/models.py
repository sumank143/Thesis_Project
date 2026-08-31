import os
import re
from abc import ABC, abstractmethod

_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def build_prompt(question: str, schema: str) -> str:
    return (
        "You are an expert at writing SQL queries.\n"
        f"Given the following database schema:\n{schema}\n\n"
        f"Write a single SQL query that answers this question:\n{question}\n"
        "Return only the SQL query, no explanation."
    )


def extract_sql(text: str) -> str:
    match = _SQL_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


class LLMClient(ABC):
    @abstractmethod
    def generate_sql(self, question: str, schema: str) -> str:
        raise NotImplementedError


class OpenAIClient(LLMClient):
    def __init__(self, model_id: str, api_key: str | None = None):
        import openai

        self._client = openai.OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self._model_id = model_id

    def generate_sql(self, question: str, schema: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model_id,
            messages=[{"role": "user", "content": build_prompt(question, schema)}],
            temperature=0,
        )
        return extract_sql(response.choices[0].message.content)


class AnthropicClient(LLMClient):
    def __init__(self, model_id: str, api_key: str | None = None):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._model_id = model_id

    def generate_sql(self, question: str, schema: str) -> str:
        response = self._client.messages.create(
            model=self._model_id,
            max_tokens=512,
            messages=[{"role": "user", "content": build_prompt(question, schema)}],
        )
        return extract_sql(response.content[0].text)


def create_client(model_cfg: dict) -> LLMClient:
    provider = model_cfg["provider"]
    if provider == "openai":
        return OpenAIClient(model_cfg["model_id"])
    if provider == "anthropic":
        return AnthropicClient(model_cfg["model_id"])
    raise ValueError(f"Unknown provider: {provider}")
