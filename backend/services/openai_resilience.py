
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

T = TypeVar("T")
RETRYABLE_ERRORS = (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)


@dataclass
class CallMetrics:
    attempts: int = 0
    latency_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


def call_with_retries(
    operation: Callable[[], T], *, max_attempts: int = 3,
    validate: Callable[[T], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[T, CallMetrics]:
    started = time.perf_counter()
    metrics = CallMetrics()
    for attempt in range(1, max_attempts + 1):
        metrics.attempts = attempt
        try:
            response = operation()
            if validate:
                validate(response)
            usage = getattr(response, "usage", None)
            metrics.input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            metrics.output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
            metrics.total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
            metrics.latency_seconds = time.perf_counter() - started
            return response, metrics
        except RETRYABLE_ERRORS:
            if attempt >= max_attempts:
                raise
            sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError("Unreachable retry state")


def validate_json_response(response) -> None:
    content = response.choices[0].message.content
    parsed = json.loads(content)
    required = {"answer", "citations", "abstained"}
    if not isinstance(parsed, dict) or not required.issubset(parsed):
        raise ValueError("Invalid structured response")
    if not isinstance(parsed["citations"], list) or not isinstance(parsed["abstained"], bool):
        raise ValueError("Invalid structured response types")
