"""Tests for CircuitBreaker status tracking and open breakers."""

from __future__ import annotations

from fetch.circuit_breaker import CircuitBreaker


def test_circuit_breaker_lifecycle() -> None:
    cb = CircuitBreaker()
    cb.reset()

    assert cb.is_open("amazon.es") is False
    assert cb.open_until("amazon.es") is None
    assert cb.open_sites() == {}
    assert cb.failure_count("amazon.es") == 0

    # Record 1 failure (threshold is 2 by default)
    cb.record_failure("amazon.es")
    assert cb.failure_count("amazon.es") == 1
    assert cb.is_open("amazon.es") is False
    assert cb.open_sites() == {}

    # Record 2nd failure -> breaker opens
    cb.record_failure("amazon.es")
    assert cb.failure_count("amazon.es") == 2
    assert cb.is_open("amazon.es") is True
    assert cb.open_until("amazon.es") is not None
    open_breakers = cb.open_sites()
    assert "amazon.es" in open_breakers

    # Success closes the breaker and resets failure count
    cb.record_success("amazon.es")
    assert cb.is_open("amazon.es") is False
    assert cb.open_until("amazon.es") is None
    assert cb.open_sites() == {}
    assert cb.failure_count("amazon.es") == 0

    cb.reset()
