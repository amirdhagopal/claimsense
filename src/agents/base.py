"""
ClaimSense AI — Base Agent Class (OpenAI SDK Integration)

Configures the standard OpenAI client to communicate seamlessly with either
local Ollama (http://localhost:11434/v1) or OpenAI cloud APIs.
"""

from __future__ import annotations

import json
import time
from typing import Any, Type, TypeVar
from openai import OpenAI
from pydantic import BaseModel

from src.config import settings

T = TypeVar("T", bound=BaseModel)


class BaseAgent:
    """
    Base class providing OpenAI SDK client interaction, strict schema parsing,
    and per-call token/latency telemetry.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.openai_model
        self.client = OpenAI(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            timeout=settings.request_timeout,
        )
        self.last_call_telemetry: dict[str, Any] = {}

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, round(len(text) / 3.8))

    def _record_telemetry(
        self,
        completion: Any,
        system_prompt: str,
        schema_json: str,
        user_prompt: str,
        output_text: str,
        elapsed_ms: float,
        parse_mode: str,
    ) -> None:
        est_sys = self._estimate_tokens(system_prompt)
        est_schema = self._estimate_tokens(schema_json)
        est_user = self._estimate_tokens(user_prompt)
        est_total_in = max(1, est_sys + est_schema + est_user)

        usage = getattr(completion, "usage", None)
        raw_prompt = getattr(usage, "prompt_tokens", None) if usage else None
        raw_completion = getattr(usage, "completion_tokens", None) if usage else None

        prompt_tokens = int(raw_prompt) if raw_prompt and raw_prompt > 0 else est_total_in
        output_tokens = int(raw_completion) if raw_completion and raw_completion > 0 else self._estimate_tokens(output_text)

        # Proportionally attribute prompt_tokens across System Instructions, JSON Schema, and Claim Context
        system_tokens = round(prompt_tokens * (est_sys / est_total_in))
        schema_tokens = round(prompt_tokens * (est_schema / est_total_in))
        context_tokens = max(0, prompt_tokens - system_tokens - schema_tokens)

        self.last_call_telemetry = {
            "agent": self.__class__.__name__,
            "model": self.model_name,
            "latency_ms": round(elapsed_ms, 1),
            "parse_mode": parse_mode,
            "prompt_tokens": prompt_tokens,
            "system_tokens": system_tokens,
            "schema_tokens": schema_tokens,
            "context_tokens": context_tokens,
            "output_tokens": output_tokens,
            "total_tokens": prompt_tokens + output_tokens,
        }

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
        t0 = time.perf_counter()
        schema_json = json.dumps(response_model.model_json_schema())

        try:
            # Primary path: beta parse
            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_model,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is not None:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                self._record_telemetry(
                    completion=completion,
                    system_prompt=system_prompt,
                    schema_json=schema_json,
                    user_prompt=user_prompt,
                    output_text=parsed.model_dump_json(),
                    elapsed_ms=elapsed_ms,
                    parse_mode="structured_parse",
                )
                return parsed
        except Exception:
            # Fallback path: standard JSON mode parsing
            pass

        # Robust JSON fallback
        augmented_system = (
            f"{system_prompt}\n\n"
            f"You MUST output valid JSON conforming strictly to this JSON Schema:\n{schema_json}"
        )
        completion = self.client.chat.completions.create(
            model=self.model_name,
            temperature=0.0,
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
            validated = response_model.model_validate_json(content)
        except Exception:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                validated = response_model.model_validate_json(content[start:end + 1])
            else:
                raise

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._record_telemetry(
            completion=completion,
            system_prompt=system_prompt,
            schema_json=schema_json,
            user_prompt=user_prompt,
            output_text=content,
            elapsed_ms=elapsed_ms,
            parse_mode="json_fallback",
        )
        return validated
