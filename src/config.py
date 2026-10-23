"""
ClaimSense AI — Application Configuration

Loads settings from environment variables with local defaults
enabling 100% offline local execution via Ollama and LocalStack.
"""

from __future__ import annotations

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # Application
    app_name: str = "ClaimSense AI"
    environment: str = os.getenv("ENVIRONMENT", "local")
    port: int = int(os.getenv("PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # LLM & OpenAI SDK Interface (supports local Ollama or OpenAI Cloud)
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "ollama")
    openai_model: str = os.getenv("OPENAI_MODEL", "llama3.2:3b")
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "45.0"))

    # AWS Observability (supports local endpoint or AWS Cloud)
    aws_endpoint_url: str | None = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    cloudwatch_namespace: str = "ClaimSenseAI"
    cloudwatch_log_group: str = "/ecs/claimsense-ai"

    # Deterministic Spine Rules
    total_loss_threshold_ratio: float = 0.75  # repair_estimate >= 0.75 * market_value


settings = Settings()
