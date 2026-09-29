"""
unit/test_scoring_golden.py — Golden vector A from §7.2.

Tests the pure scoring module against the spec's golden numbers.
These must always pass; they pin the scoring formula.
"""
from __future__ import annotations

import pytest
from pramana.scoring.api import (
    CheckOutcome,
    CheckStatus,
    ScoreComponents,
    TrustLevel,
    compute_score,
    format_score,
)


# ─── Golden vector A (§7.2) ───────────────────────────────────────────────────
# | Check | Weight | Result | Trust          |
# | C1    | 20     | PASS   | DETERMINISTIC  |
# | C2    | 10     | FAIL   | DETERMINISTIC  |
# | C3    | 5      | PASS   | CORROBORATED   |
# | C4    | 10     | PASS   | PROVISIONAL    |
# | C5    | 2      | FAIL   | PROVISIONAL    |
#
# Verified = 25/35 → 71.4
# Provisional-Inclusive = 35/47 → 74.5
# Provisional dependence = 12/47 → 25.5

GOLDEN_A_OUTCOMES = [
    CheckOutcome("C1", "dev1", 20, CheckStatus.PASS, TrustLevel.DETERMINISTIC, ()),
    CheckOutcome("C2", "dev1", 10, CheckStatus.FAIL, TrustLevel.DETERMINISTIC, ()),
    CheckOutcome("C3", "dev1",  5, CheckStatus.PASS, TrustLevel.CORROBORATED, ()),
    CheckOutcome("C4", "dev1", 10, CheckStatus.PASS, TrustLevel.PROVISIONAL, ()),
    CheckOutcome("C5", "dev1",  2, CheckStatus.FAIL, TrustLevel.PROVISIONAL, ()),
]


@pytest.mark.inv("INV-07")
def test_golden_vector_a_verified() -> None:
    """Verified score must be 25/35 per §7.2 golden vector A."""
    sc = compute_score(GOLDEN_A_OUTCOMES)
    assert sc.verified_numerator == 25
    assert sc.verified_denominator == 35


@pytest.mark.inv("INV-07")
def test_golden_vector_a_provisional_inclusive() -> None:
    """Provisional-Inclusive score must be 35/47 per §7.2."""
    sc = compute_score(GOLDEN_A_OUTCOMES)
    assert sc.provisional_inclusive_numerator == 35
    assert sc.provisional_inclusive_denominator == 47


@pytest.mark.inv("INV-07")
def test_golden_vector_a_provisional_dependence() -> None:
    """Provisional dependence must be 12/47 per §7.2."""
    sc = compute_score(GOLDEN_A_OUTCOMES)
    assert sc.provisional_dependence_numerator == 12
    assert sc.provisional_dependence_denominator == 47


@pytest.mark.inv("INV-07")
def test_golden_vector_a_formatted_percentages() -> None:
    """Formatted percentages must match §7.2: 71.4, 74.5, 25.5."""
    sc = compute_score(GOLDEN_A_OUTCOMES)
    fmt = format_score(sc)
    assert fmt["verified"] == "71.4"
    assert fmt["provisional_inclusive"] == "74.5"
    assert fmt["provisional_dependence"] == "25.5"


@pytest.mark.inv("INV-07")
def test_two_numbers_never_blended() -> None:
    """ScoreComponents must NOT have a 'blended' or 'discounted' attribute."""
    sc = compute_score(GOLDEN_A_OUTCOMES)
    assert not hasattr(sc, "blended"), "blended field found — INV-07 violation"
    assert not hasattr(sc, "discounted_score"), "discounted_score found — INV-07 violation"
    assert not hasattr(sc, "confidence_multiplier"), "confidence_multiplier found — INV-07 violation"


@pytest.mark.inv("INV-07")
def test_empty_denominator_returns_none() -> None:
    """With no evaluated outcomes, scores must be None (rendered 'n/a'), not 0 or 100."""
    sc = compute_score([])
    fmt = format_score(sc)
    assert fmt["verified"] == "None"
    assert fmt["provisional_inclusive"] == "None"


def test_unevaluated_excluded_from_all_scores() -> None:
    """UNEVALUATED outcomes must not contribute to any denominator."""
    outcomes = [
        CheckOutcome("C1", "dev1", 20, CheckStatus.PASS, TrustLevel.DETERMINISTIC, ()),
        CheckOutcome("C2", "dev1", 10, CheckStatus.UNEVALUATED, TrustLevel.DETERMINISTIC, ()),
    ]
    sc = compute_score(outcomes)
    # Only C1 should count
    assert sc.verified_denominator == 20
    assert sc.provisional_inclusive_denominator == 20


def test_no_provisional_verified_equals_provisional_inclusive() -> None:
    """With no PROVISIONAL checks, Verified must equal Provisional-Inclusive."""
    outcomes = [
        CheckOutcome("C1", "dev1", 20, CheckStatus.PASS, TrustLevel.DETERMINISTIC, ()),
        CheckOutcome("C2", "dev1", 10, CheckStatus.FAIL, TrustLevel.CORROBORATED, ()),
    ]
    sc = compute_score(outcomes)
    assert sc.verified_numerator == sc.provisional_inclusive_numerator
    assert sc.verified_denominator == sc.provisional_inclusive_denominator


def test_adding_provisional_pass_does_not_change_verified() -> None:
    """Adding a PROVISIONAL PASS must not change the Verified score (INV-07 monotonicity)."""
    base_outcomes = [
        CheckOutcome("C1", "dev1", 20, CheckStatus.PASS, TrustLevel.DETERMINISTIC, ()),
    ]
    with_provisional = base_outcomes + [
        CheckOutcome("C2", "dev1", 10, CheckStatus.PASS, TrustLevel.PROVISIONAL, ()),
    ]
    sc_base = compute_score(base_outcomes)
    sc_with = compute_score(with_provisional)

    # Verified numerator and denominator must stay the same
    assert sc_base.verified_numerator == sc_with.verified_numerator
    assert sc_base.verified_denominator == sc_with.verified_denominator
