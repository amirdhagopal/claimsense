"""
ClaimSense AI — Base Agent Class (OpenAI SDK Integration)

Configures the standard OpenAI client to communicate seamlessly with either
local Ollama (http://localhost:11434/v1) or OpenAI cloud APIs.
"""

from __future__ import annotations

import json
from typing import Type, TypeVar
from openai import OpenAI
from pydantic import BaseModel

from src.config import settings

T = TypeVar("T", bound=BaseModel)


class BaseAgent:
    """
    Base class providing OpenAI SDK client interaction and strict schema parsing.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.openai_model
        self.client = OpenAI(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            timeout=settings.request_timeout,
        )

    def generate_typed_response(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
    ) -> T:
        """
        Executes chat completion with strict typed response parsing.
        Uses client.beta.chat.completions.parse with automatic fallback to JSON mode.
        """
        try:
            # Primary path: beta parse
            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_model,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is not None:
                return parsed
        except Exception as e:
            # Fallback path: standard JSON mode parsing
            pass

        # Robust JSON fallback
        schema_json = json.dumps(response_model.model_json_schema())
        augmented_system = (
            f"{system_prompt}\n\n"
            f"You MUST output valid JSON conforming strictly to this JSON Schema:\n{schema_json}"
        )
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": augmented_system},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or "{}"
        content = content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        try:
            return response_model.model_validate_json(content)
        except Exception:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                return response_model.model_validate_json(content[start:end + 1])
            raise
