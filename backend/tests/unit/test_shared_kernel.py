"""
unit/test_shared_kernel.py — shared_kernel unit tests.
"""
from __future__ import annotations

import pytest
from pramana.shared_kernel.api import (
    Severity,
    TrustClass,
    sha256_bytes,
    sha256_str,
    canonical_json,
    PramanaError,
    ValidationError,
    NotFoundError,
    InvariantViolation,
    NullEventBus,
    DomainEvent,
    new_id,
)


def test_severity_weights() -> None:
    assert Severity.CRITICAL.weight == 20
    assert Severity.HIGH.weight == 10
    assert Severity.MEDIUM.weight == 5
    assert Severity.LOW.weight == 2


def test_sha256_bytes_deterministic() -> None:
    data = b"hello world"
    assert sha256_bytes(data) == sha256_bytes(data)
    assert len(sha256_bytes(data)) == 64  # hex digest


def test_sha256_str_deterministic() -> None:
    assert sha256_str("hello") == sha256_str("hello")
    assert sha256_str("hello") != sha256_str("world")


def test_canonical_json_sorted_keys() -> None:
    a = canonical_json({"z": 1, "a": 2})
    b = canonical_json({"a": 2, "z": 1})
    assert a == b
    assert '"a":2' in a.decode("utf-8")


def test_error_hierarchy() -> None:
    assert issubclass(ValidationError, PramanaError)
    assert issubclass(NotFoundError, PramanaError)
    assert issubclass(InvariantViolation, PramanaError)


def test_null_event_bus_no_op() -> None:
    bus = NullEventBus()
    event = DomainEvent()
    bus.publish(event)  # must not raise


def test_new_id_unique() -> None:
    ids = {new_id() for _ in range(100)}
    assert len(ids) == 100


@pytest.mark.inv("INV-11")
def test_trust_class_ordering() -> None:
    """PROVISIONAL < CORROBORATED < DETERMINISTIC."""
    order = [TrustClass.PROVISIONAL, TrustClass.CORROBORATED, TrustClass.DETERMINISTIC]
    assert order == sorted(order, key=lambda x: list(TrustClass).index(x))
