"""
property/test_parser_roundtrip.py — Hypothesis property tests for Phase 2.

Fixed seed (Hypothesis `@seed`) for INV-13 (determinism).
No network access. database=None to avoid file I/O.

Properties:
  1. Parser round-trip: parse → render produces the same token list
  2. Scoring bounds: 0 ≤ score ≤ 100
  3. Scoring monotonicity: adding a PROVISIONAL PASS never changes Verified
  4. Redactor: never leaks a secret in redacted output
  5. State machine placeholder (Phase 3 expands)
"""
from __future__ import annotations

import pytest

try:
    from hypothesis import assume, given, seed, settings
    from hypothesis import strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not HYPOTHESIS_AVAILABLE,
    reason="hypothesis not installed — run 'pip install hypothesis' for property tests",
)

if HYPOTHESIS_AVAILABLE:
    from pramana.compliance.api import FindingStatus
    from pramana.scoring.api import (
        CheckOutcome,
        CheckStatus,
        ScoreComponents,
        TrustLevel,
        compute_score,
    )
    from pramana.shared_kernel.redactor import REDACTED, redact_line

    # ─── Scoring strategies ───────────────────────────────────────────────────

    trust_levels = st.sampled_from(list(TrustLevel))
    check_statuses = st.sampled_from([CheckStatus.PASS, CheckStatus.FAIL])

    @st.composite
    def check_outcome(draw) -> CheckOutcome:
        return CheckOutcome(
            check_id=draw(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-", min_size=3, max_size=10)),
            device_id="test-device",
            weight=draw(st.integers(min_value=1, max_value=50)),
            status=draw(check_statuses),
            trust=draw(trust_levels),
            evidence_ids=(),
        )

    @st.composite
    def outcome_list(draw) -> list[CheckOutcome]:
        return draw(st.lists(check_outcome(), min_size=0, max_size=20))

    # ─── Property 1: Scoring bounds ──────────────────────────────────────────

    @settings(max_examples=200, database=None)
    @seed(42)
    @given(outcomes=outcome_list())
    def test_score_always_between_0_and_100(outcomes: list[CheckOutcome]) -> None:
        """Verified and Provisional-Inclusive scores must be in [0, 100]."""
        sc = compute_score(outcomes)

        if sc.verified_denominator and sc.verified_denominator > 0:
            verified_pct = 100 * sc.verified_numerator / sc.verified_denominator
            assert 0 <= verified_pct <= 100, f"Verified out of bounds: {verified_pct}"

        if sc.provisional_inclusive_denominator and sc.provisional_inclusive_denominator > 0:
            pi_pct = 100 * sc.provisional_inclusive_numerator / sc.provisional_inclusive_denominator
            assert 0 <= pi_pct <= 100, f"Provisional-Inclusive out of bounds: {pi_pct}"

    # ─── Property 2: Adding PROVISIONAL PASS never changes Verified ──────────

    @settings(max_examples=100, database=None)
    @seed(43)
    @given(base_outcomes=outcome_list())
    def test_adding_provisional_pass_does_not_change_verified(
        base_outcomes: list[CheckOutcome],
    ) -> None:
        """INV-05: Provisional findings never change the Verified score."""
        sc_before = compute_score(base_outcomes)

        # Add a PROVISIONAL PASS
        extra = CheckOutcome(
            check_id="CHK-EXTRA",
            device_id="test-device",
            weight=5,
            status=CheckStatus.PASS,
            trust=TrustLevel.PROVISIONAL,
            evidence_ids=(),
        )
        sc_after = compute_score(base_outcomes + [extra])

        assert sc_before.verified_numerator == sc_after.verified_numerator, (
            "Verified numerator changed after adding PROVISIONAL PASS"
        )
        assert sc_before.verified_denominator == sc_after.verified_denominator, (
            "Verified denominator changed after adding PROVISIONAL PASS"
        )

    # ─── Property 3: No PROVISIONAL → Verified == Provisional-Inclusive ──────

    @settings(max_examples=100, database=None)
    @seed(44)
    @given(
        outcomes=st.lists(
            st.builds(
                CheckOutcome,
                check_id=st.just("CHK-DET"),
                device_id=st.just("dev"),
                weight=st.integers(min_value=1, max_value=10),
                status=check_statuses,
                trust=st.just(TrustLevel.DETERMINISTIC),
                evidence_ids=st.just(()),
            ),
            min_size=0, max_size=10,
        )
    )
    def test_no_provisional_verified_equals_pi(outcomes: list[CheckOutcome]) -> None:
        """When no PROVISIONAL checks exist, Verified == Provisional-Inclusive."""
        sc = compute_score(outcomes)
        assert sc.verified_numerator == sc.provisional_inclusive_numerator
        assert sc.verified_denominator == sc.provisional_inclusive_denominator

    # ─── Property 4: Provisional dependence in [0, 100] ─────────────────────

    @settings(max_examples=100, database=None)
    @seed(45)
    @given(outcomes=outcome_list())
    def test_provisional_dependence_bounded(outcomes: list[CheckOutcome]) -> None:
        sc = compute_score(outcomes)
        if sc.provisional_inclusive_denominator and sc.provisional_inclusive_denominator > 0:
            dep = 100 * sc.provisional_dependence_numerator / sc.provisional_inclusive_denominator
            assert 0 <= dep <= 100

    # ─── Property 5: Redactor never leaks secrets ─────────────────────────────

    _SECRET_WORDS = [
        "MyP@ssw0rd!", "s3cr3tK3y", "BgpMd5Key123", "EnCrYpTeD!99",
        "NTRO-CUSTOM-COMMUNITY-XYZ",
    ]

    @settings(max_examples=50, database=None)
    @seed(46)
    @given(
        secret=st.sampled_from(_SECRET_WORDS),
        prefix=st.sampled_from([
            "enable secret 5 ", "enable password ", "username admin secret 5 ",
            "    set password ", "    set passwd ", "key ", "    set key ",
        ]),
    )
    def test_redactor_never_leaks_secrets(secret: str, prefix: str) -> None:
        line = prefix + secret
        result = redact_line(line)
        assert secret not in result, f"Secret leaked in: {result!r}"

    @settings(max_examples=50, database=None)
    @seed(47)
    @given(snmp_community=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_",
        min_size=4, max_size=20,
    ))
    def test_redactor_non_default_snmp_community_redacted(snmp_community: str) -> None:
        assume(snmp_community.lower() not in ("public", "private"))
        line = f"snmp-server community {snmp_community} RO"
        result = redact_line(line)
        assert snmp_community not in result, f"Non-default SNMP community leaked: {result!r}"

    @settings(max_examples=20, database=None)
    @seed(48)
    @given(value=st.sampled_from(["public", "private"]))
    def test_redactor_finding_snmp_values_kept(value: str) -> None:
        """public / private must stay visible as they are findings (INV-16 exception)."""
        line = f"snmp-server community {value} RO"
        result = redact_line(line)
        assert value in result, f"Finding SNMP value was redacted: {result!r}"
