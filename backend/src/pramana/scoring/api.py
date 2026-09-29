"""
scoring.api — Two-number scoring model (INV-07).

Public exports:
  - TrustLevel, CheckStatus, CheckOutcome
  - ScoreComponents, compute_score, format_score

Rules (§7.2 / INV-07):
  - Verified score: PASS weight / total evaluated weight,
    excluding PROVISIONAL and UNEVALUATED checks.
  - Provisional-Inclusive score: PASS weight / total evaluated weight,
    including PROVISIONAL checks.
  - Provisional dependence: provisional PASS weight / total P-I denominator.
  - No blended score, no discount constants, no confidence multipliers.
  - UNEVALUATED outcomes excluded from all denominators.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


# ─── Enums ────────────────────────────────────────────────────────────────────

class TrustLevel(str, Enum):
    """Trust level for a check outcome (maps to mapping state / evidence)."""
    DETERMINISTIC = "deterministic"   # Hand-written grammar
    CORROBORATED = "corroborated"     # Gate passed + corroboration evidence
    PROVISIONAL = "provisional"       # Gate passed, not yet corroborated


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNEVALUATED = "unevaluated"


# ─── Inputs ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CheckOutcome:
    """One check evaluation result for a single device."""
    check_id: str
    device_id: str
    weight: int
    status: CheckStatus
    trust: TrustLevel
    evidence_ids: tuple[str, ...]


# ─── Outputs ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ScoreComponents:
    """
    The two-number score (INV-07). Never blended, never discounted.

    verified_*:            excludes PROVISIONAL checks entirely.
    provisional_inclusive_*: includes PROVISIONAL checks.
    provisional_dependence_*: provisional PASS weight vs P-I denominator.
    """
    verified_numerator: int | None
    verified_denominator: int | None
    provisional_inclusive_numerator: int | None
    provisional_inclusive_denominator: int | None
    provisional_dependence_numerator: int | None
    provisional_dependence_denominator: int | None


# ─── Pure scoring function ────────────────────────────────────────────────────

def compute_score(outcomes: Sequence[CheckOutcome]) -> ScoreComponents:
    """
    Compute the two-number score from a sequence of CheckOutcomes.

    Pure function: same inputs → same outputs.
    No network, no DB, no side-effects.
    """
    # Only evaluated outcomes contribute
    evaluated = [o for o in outcomes if o.status != CheckStatus.UNEVALUATED]
    non_provisional = [o for o in evaluated if o.trust != TrustLevel.PROVISIONAL]

    # Verified score (excludes PROVISIONAL)
    v_denom = sum(o.weight for o in non_provisional)
    v_num = sum(o.weight for o in non_provisional if o.status == CheckStatus.PASS)

    # Provisional-Inclusive score (includes PROVISIONAL)
    pi_denom = sum(o.weight for o in evaluated)
    pi_num = sum(o.weight for o in evaluated if o.status == CheckStatus.PASS)

    # Provisional dependence: total provisional weight (pass+fail) vs P-I denominator
    prov_pass_weight = sum(
        o.weight
        for o in evaluated
        if o.trust == TrustLevel.PROVISIONAL
    )

    return ScoreComponents(
        verified_numerator=v_num if v_denom > 0 else None,
        verified_denominator=v_denom if v_denom > 0 else None,
        provisional_inclusive_numerator=pi_num if pi_denom > 0 else None,
        provisional_inclusive_denominator=pi_denom if pi_denom > 0 else None,
        provisional_dependence_numerator=prov_pass_weight if pi_denom > 0 else None,
        provisional_dependence_denominator=pi_denom if pi_denom > 0 else None,
    )


def format_score(sc: ScoreComponents) -> dict[str, str]:
    """
    Format ScoreComponents as rounded percentage strings for API / PDF.

    Returns "None" for absent scores (not "n/a" or 0) so callers can detect
    the absence and render appropriately.
    """
    def _pct(num: int | None, denom: int | None) -> str:
        if num is None or denom is None or denom == 0:
            return "None"
        return f"{num / denom * 100:.1f}"

    return {
        "verified": _pct(sc.verified_numerator, sc.verified_denominator),
        "provisional_inclusive": _pct(
            sc.provisional_inclusive_numerator,
            sc.provisional_inclusive_denominator,
        ),
        "provisional_dependence": _pct(
            sc.provisional_dependence_numerator,
            sc.provisional_dependence_denominator,
        ),
    }
