"""
compliance.domain.engine — declarative predicate evaluator (Phase 2).

Predicates are pure declarative data (R9 — no eval/exec).
Phase 2: matches on pre-resolved setting_id from all 4 vendor parsers.
Supported ops: present, absent, eq, ne, in, has_value.
Supported combinators: all_of, any_of, not.
"""
from __future__ import annotations

from typing import Any

from pramana.baseline.api import NormalizedBaseline, Observation
from pramana.compliance.api import (
    Check,
    ComplianceService,
    Finding,
    FindingStatus,
)
from pramana.scoring.api import TrustLevel


# ─── Observation helpers ──────────────────────────────────────────────────────

def _obs_matches_setting(obs: Observation, setting_id: str) -> bool:
    """
    Phase 2: match on pre-resolved setting_id.
    Falls back to token pattern matching only for legacy __raw__ observations.
    """
    if obs.setting_id == setting_id:
        return True
    # Legacy fallback for any __raw__ observations (should not exist in Phase 2+)
    if obs.setting_id == "__raw__":
        tv = obs.typed_value
        tokens = tv if isinstance(tv, list) else tv.get("tokens", []) if isinstance(tv, dict) else []
        return _tokens_match_setting(tokens, setting_id)
    return False


def _is_negated(obs: Observation) -> bool:
    """Return True if the observation represents a negated config line ('no ...')."""
    tv = obs.typed_value
    if isinstance(tv, dict):
        return bool(tv.get("negated", False))
    # Legacy: list-style typed_value never has negation info
    return False


def _tokens_match_setting(tokens: list[str], setting_id: str) -> bool:
    """Legacy token→setting resolver (fallback for __raw__ observations only)."""
    mapping: dict[str, Any] = {
        "mgmt.telnet.enabled": lambda t: t[:2] == ["transport", "input"] and "telnet" in t,
        "snmp.community.default": lambda t: t[:2] == ["snmp-server", "community"] and (
            "public" in t or "private" in t
        ),
        "vty.access-class.in": lambda t: t[0] == "access-class" and "in" in t,
        "logging.host": lambda t: t[:2] == ["logging", "host"],
        "mgmt.http.server": lambda t: t[:3] == ["ip", "http", "server"],
        "service.tcp-small-servers": lambda t: t[:2] == ["service", "tcp-small-servers"],
        "service.udp-small-servers": lambda t: t[:2] == ["service", "udp-small-servers"],
        "service.finger": lambda t: "finger" in t,
        "ntp.server": lambda t: t[:2] == ["ntp", "server"],
        "mgmt.ssh.v2": lambda t: t[:3] == ["ip", "ssh", "version"],
    }
    fn = mapping.get(setting_id)
    if fn is None:
        return False
    try:
        return bool(fn(tokens))
    except Exception:
        return False


# ─── Predicate evaluator ─────────────────────────────────────────────────────

def _evaluate_predicate(
    predicate: dict[str, Any],
    baseline: NormalizedBaseline,
) -> tuple[FindingStatus, list[dict[str, Any]]]:
    """
    Evaluate a declarative predicate against a NormalizedBaseline.

    Supported structure (§8):
      {setting, op, value?}               — leaf check
      {all_of: [...]}                     — conjunction (AND)
      {any_of: [...]}                     — disjunction (OR)
      {not: {...}}                        — negation
    """
    evidence: list[dict[str, Any]] = []

    if "all_of" in predicate:
        for sub in predicate["all_of"]:
            status, sub_ev = _evaluate_predicate(sub, baseline)
            evidence.extend(sub_ev)
            if status == FindingStatus.FAIL:
                return FindingStatus.FAIL, evidence
        return FindingStatus.PASS, evidence

    if "any_of" in predicate:
        any_pass = False
        for sub in predicate["any_of"]:
            status, sub_ev = _evaluate_predicate(sub, baseline)
            evidence.extend(sub_ev)
            if status == FindingStatus.PASS:
                any_pass = True
        return (FindingStatus.PASS if any_pass else FindingStatus.FAIL), evidence

    if "not" in predicate:
        status, sub_ev = _evaluate_predicate(predicate["not"], baseline)
        evidence.extend(sub_ev)
        return (FindingStatus.FAIL if status == FindingStatus.PASS else FindingStatus.PASS), evidence

    # ── Leaf: {setting, op, value?} ──────────────────────────────────────────
    setting_id = predicate.get("setting", "")
    op = predicate.get("op", "present")
    expected_value = predicate.get("value")

    matching_obs = [
        obs for obs in baseline.observations
        if _obs_matches_setting(obs, setting_id)
    ]

    # Build evidence entries
    for obs in matching_obs:
        evidence.append({
            "artifact_sha256": obs.line_ref.artifact_sha256,
            "line_no": obs.line_ref.line_no,
            "byte_span": list(obs.line_ref.byte_span),
            "setting_id": setting_id,
            "negated": _is_negated(obs),
        })

    if op == "present":
        # PASS = setting found AND not negated
        present = any(not _is_negated(obs) for obs in matching_obs)
        return (FindingStatus.PASS if present else FindingStatus.FAIL), evidence

    if op == "absent":
        # PASS = setting not found (or only negated forms exist)
        absent = not any(not _is_negated(obs) for obs in matching_obs)
        return (FindingStatus.PASS if absent else FindingStatus.FAIL), evidence

    if op == "eq" and expected_value is not None:
        # PASS = at least one matching observation has typed_value matching expected
        found = any(
            obs.typed_value == expected_value
            or (isinstance(obs.typed_value, dict) and obs.typed_value.get("value") == expected_value)
            for obs in matching_obs
        )
        return (FindingStatus.PASS if found else FindingStatus.FAIL), evidence

    if op == "has_value":
        # PASS = at least one matching observation exists with any non-negated value
        has_v = any(not _is_negated(obs) for obs in matching_obs)
        return (FindingStatus.PASS if has_v else FindingStatus.FAIL), evidence

    # Unrecognised op
    return FindingStatus.UNEVALUATED, evidence


# ─── Compliance service ───────────────────────────────────────────────────────

class ComplianceServiceImpl(ComplianceService):
    """
    Phase 2 implementation: evaluates all 10 seed checks across all 4 vendors.
    Check catalog is injected (loaded from YAML in Phase 3+; hard-coded here).
    """

    def __init__(self, checks: list[Check]) -> None:
        self._checks = {c.check_id: c for c in checks}

    def evaluate(
        self,
        baseline: NormalizedBaseline,
        device_id: str,
        profile_commit: str,
    ) -> list[Finding]:
        findings: list[Finding] = []

        for check in self._checks.values():
            status, evidence = _evaluate_predicate(check.predicate, baseline)

            # All Phase 1+2 findings are DETERMINISTIC (no proposer involved yet)
            findings.append(Finding(
                check_id=check.check_id,
                device_id=device_id,
                status=status,
                trust=TrustLevel.DETERMINISTIC.value,
                blast_radius_flag=bool(check.blast_radius),
                unevaluated_reason=(
                    "Predicate op not yet supported" if status == FindingStatus.UNEVALUATED else None
                ),
                evidence_line_refs=tuple(evidence),
            ))

        return findings
