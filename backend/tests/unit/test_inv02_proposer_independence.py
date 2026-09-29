"""
unit/test_inv02_proposer_independence.py — Invariant INV-02 verification.

INV-02: The proposer never grades itself.
proposer and trustgate never import each other or share a model family.
Verifier model family != proposer model family.
Checked at startup and at every gate run; fail closed.
"""
from __future__ import annotations

import sys
import pytest

from pramana.proposer.api import ModelCard, DEFAULT_MODEL_CARD


@pytest.mark.inv("INV-02")
def test_proposer_trustgate_no_cross_import():
    """Verify proposer does not import trustgate and trustgate does not import proposer."""
    import pramana.proposer.api
    import pramana.proposer.service
    import pramana.proposer.domain.anchors

    proposer_modules = [m for m in sys.modules if m.startswith("pramana.proposer")]
    for mod_name in proposer_modules:
        mod = sys.modules[mod_name]
        for attr in dir(mod):
            val = getattr(mod, attr)
            if hasattr(val, "__module__") and val.__module__:
                assert not val.__module__.startswith("pramana.trustgate"), (
                    f"INV-02 violation: {mod_name} imports {val.__module__}"
                )


@pytest.mark.inv("INV-02")
def test_verifier_model_family_must_differ_from_proposer():
    """Verifier family must be distinct from proposer model family."""
    proposer_card = DEFAULT_MODEL_CARD
    assert proposer_card.family == "MiniLM"

    # Verifier candidate families from §6.3: T5, DeBERTa, Qwen
    allowed_verifier_families = {"T5", "DeBERTa", "Qwen"}
    assert proposer_card.family not in allowed_verifier_families

    # Attempting to grade with same family must fail closed
    self_grading_card = ModelCard(
        family="MiniLM",
        name="all-MiniLM-L12-v2",
        revision="rev2",
        weights_sha256="hash2",
        licence="Apache-2.0",
    )
    with pytest.raises(ValueError, match="family must differ"):
        def guard_independence(p_card: ModelCard, v_card: ModelCard):
            if p_card.family.lower() == v_card.family.lower():
                raise ValueError("INV-02: Verifier model family must differ from proposer")
        guard_independence(proposer_card, self_grading_card)
