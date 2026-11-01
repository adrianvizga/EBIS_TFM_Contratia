import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from services.openai_resilience import call_with_retries, validate_json_response


def _response(content='{"answer":"ok","citations":[],"abstained":false}'):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def test_timeout_retries_and_counts_success_once():
    request = Mock()
    operation = Mock(side_effect=[APITimeoutError(request=request), _response()])
    response, metrics = call_with_retries(operation, sleep=lambda _: None)
    assert response.usage.total_tokens == 15
    assert metrics.attempts == 2
    assert metrics.total_tokens == 15


def test_rate_limit_exhaustion_has_no_usage_recorded():
    request = Mock()
    operation = Mock(side_effect=RateLimitError("limited", response=Mock(status_code=429, headers={}), body=None))
    with pytest.raises(RateLimitError):
        call_with_retries(operation, max_attempts=2, sleep=lambda _: None)
    assert operation.call_count == 2


def test_connection_unavailable_retries_then_fails():
    operation = Mock(side_effect=APIConnectionError(request=Mock()))
    with pytest.raises(APIConnectionError):
        call_with_retries(operation, max_attempts=3, sleep=lambda _: None)
    assert operation.call_count == 3


@pytest.mark.parametrize("content", ["not json", "{}", '{"answer":1,"citations":"bad","abstained":"no"}'])
def test_invalid_response_is_rejected(content):
    with pytest.raises((ValueError, json.JSONDecodeError)):
        validate_json_response(_response(content))


def test_non_retryable_invalid_response_is_not_retried():
    operation = Mock(return_value=_response("{}"))
    with pytest.raises(ValueError):
        call_with_retries(operation, validate=validate_json_response, sleep=lambda _: None)
    assert operation.call_count == 1
