from __future__ import annotations

import hashlib

from evaluator_harness.config import ModelConfig
from evaluator_harness.providers.base import ModelRequest, ModelResponse


class DryRunProvider:
    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    def generate(self, request: ModelRequest) -> ModelResponse:
        item_id = str(request.metadata.get("item_id") or "unknown")
        prompt_text = (
            getattr(request.rendered_prompt, "display_text", None)
            if request.rendered_prompt is not None
            else request.prompt
        )
        digest = hashlib.sha256(str(prompt_text).encode("utf-8")).hexdigest()[:12]
        return ModelResponse(
            output=f"[dry-run:{self.config.name}:{item_id}:{digest}]",
            latency_ms=0,
            input_tokens=None,
            output_tokens=None,
            cost_usd=0.0,
            raw={
                "dry_run": True,
                "tracing_strategy": "synthetic",
                "retry_count": 0,
                "prompt_shape": (
                    getattr(request.rendered_prompt, "shape", "text")
                    if request.rendered_prompt is not None
                    else "text"
                ),
            },
        )
