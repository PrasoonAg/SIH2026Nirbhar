"""
unit/test_inv12_ledger_chaining.py — Invariant INV-12 verification.

INV-12: Every state transition is ledgered: timestamp, actor, SHA-256 forward link.
Tamper test: Flip any byte in any entry and chain verification fails.
"""
from __future__ import annotations

import copy
from uuid import uuid4
import pytest

from pramana.ledger.api import (
    LedgerEntry,
    create_entry,
    verify_chain,
)
from pramana.ledger.adapters.in_memory import InMemoryLedgerAdapter


@pytest.mark.inv("INV-12")
def test_ledger_single_entry_chain_valid():
    mapping_id = uuid4()
    actor_id = uuid4()
    entry = create_entry(
        sequence=1,
        mapping_id=mapping_id,
        actor_id=actor_id,
        event_kind="LineUnrecognized",
        payload={"line": "spanning-tree portfast default"},
        prev_hash="",
    )

    assert entry.sequence == 1
    assert entry.entry_hash != ""
    assert entry.prev_hash == ""
    assert verify_chain([entry]) is True


@pytest.mark.inv("INV-12")
def test_ledger_multi_entry_forward_links():
    mapping_id = uuid4()
    actor_admin = uuid4()
    actor_gate = uuid4()

    e1 = create_entry(1, mapping_id, actor_admin, "LineUnrecognized", {"raw": "line1"}, "")
    e2 = create_entry(2, mapping_id, actor_admin, "AnchorMatched", {"target": "stp.portfast"}, e1.entry_hash)
    e3 = create_entry(3, mapping_id, actor_admin, "AdminConfirmed", {"target": "stp.portfast"}, e2.entry_hash)
    e4 = create_entry(4, mapping_id, actor_gate, "GateFired", {"model": "MiniLM"}, e3.entry_hash)
    e5 = create_entry(5, mapping_id, actor_gate, "GatePassed", {"verdict": "PASS"}, e4.entry_hash)

    chain = [e1, e2, e3, e4, e5]
    assert verify_chain(chain) is True

    # Adapter verification
    adapter = InMemoryLedgerAdapter()
    for e in chain:
        adapter.append(e)

    assert adapter.verify_chain(mapping_id) is True
    assert len(adapter.entries_for(mapping_id)) == 5


@pytest.mark.inv("INV-12")
def test_ledger_tamper_detection_fails_verification():
    mapping_id = uuid4()
    actor_id = uuid4()

    e1 = create_entry(1, mapping_id, actor_id, "LineUnrecognized", {"raw": "cmd 1"}, "")
    e2 = create_entry(2, mapping_id, actor_id, "AdminConfirmed", {"target": "cmd 1"}, e1.entry_hash)
    e3 = create_entry(3, mapping_id, actor_id, "GatePassed", {"verdict": "PASS"}, e2.entry_hash)

    chain = [e1, e2, e3]
    assert verify_chain(chain) is True

    # Tamper 1: modify payload of e2
    tampered_e2 = copy.deepcopy(e2)
    tampered_e2.payload["target"] = "MALICIOUS_OVERRIDE"
    assert verify_chain([e1, tampered_e2, e3]) is False

    # Tamper 2: break forward link in e3
    tampered_e3 = copy.deepcopy(e3)
    tampered_e3.prev_hash = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    assert verify_chain([e1, e2, tampered_e3]) is False

    # Tamper 3: reorder entries
    assert verify_chain([e2, e1, e3]) is False

    # Tamper 4: omit an intermediate entry
    assert verify_chain([e1, e3]) is False
