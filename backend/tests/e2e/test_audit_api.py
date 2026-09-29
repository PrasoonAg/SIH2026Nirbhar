"""
e2e/test_audit_api.py — End-to-end Phase 1 API tests.

Tests the full upload → audit → score → findings flow via TestClient.
No real HTTP server needed (FastAPI TestClient uses HTTPX internally).

Phase 1 exit gate requirements:
  - Cisco fixture gives expected findings with line numbers
  - openapi.json can be exported and generated client compiles
  - Golden vector A passes (already tested in test_scoring_golden.py)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pramana.bootstrap.main import create_application

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "configs" / "cisco_ios"


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a TestClient with a fresh app instance."""
    # Reset DI singletons for this module so state doesn't leak between test modules
    import pramana.bootstrap.dependencies as deps
    from pramana.compliance.domain.engine import ComplianceServiceImpl
    from pramana.compliance.domain.seed_checks import SEED_CHECKS_PHASE1
    from pramana.ingest.service import IngestServiceImpl
    from pramana.parsing.service import ParsingServiceImpl
    from pramana.pipeline.service import PipelineServiceImpl

    deps._ingest_svc = IngestServiceImpl()
    deps._parsing_svc = ParsingServiceImpl()
    deps._compliance_svc = ComplianceServiceImpl(SEED_CHECKS_PHASE1)
    deps._pipeline_svc = PipelineServiceImpl(
        ingest_svc=deps._ingest_svc,
        parsing_svc=deps._parsing_svc,
        compliance_svc=deps._compliance_svc,
    )
    app = create_application()
    return TestClient(app, raise_server_exceptions=True)


# ─── Health ───────────────────────────────────────────────────────────────────

def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ─── Upload ───────────────────────────────────────────────────────────────────

def test_upload_cisco_findings_fixture(client: TestClient) -> None:
    """Upload the findings fixture and get back a valid artifact."""
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    r = client.post(
        "/api/v1/ingest/file",
        files={"file": ("test_findings.cfg", raw, "text/plain")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "test_findings.cfg"
    assert len(body["sha256"]) == 64
    assert body["size_bytes"] == len(raw)
    assert body["artifact_id"]


def test_upload_deduplication(client: TestClient) -> None:
    """Uploading the same file twice returns the same artifact_id."""
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    r1 = client.post(
        "/api/v1/ingest/file",
        files={"file": ("a.cfg", raw, "text/plain")},
    )
    r2 = client.post(
        "/api/v1/ingest/file",
        files={"file": ("b.cfg", raw, "text/plain")},
    )
    assert r1.json()["artifact_id"] == r2.json()["artifact_id"]


@pytest.mark.inv("INV-09")
def test_upload_empty_file_rejected(client: TestClient) -> None:
    """Empty files must be rejected with 400."""
    r = client.post(
        "/api/v1/ingest/file",
        files={"file": ("empty.cfg", b"", "text/plain")},
    )
    assert r.status_code == 400


# ─── Full audit flow — findings fixture ───────────────────────────────────────

@pytest.fixture(scope="module")
def findings_audit_result(client: TestClient) -> dict:
    """Upload findings fixture and run an audit; cache the result."""
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    up = client.post(
        "/api/v1/ingest/file",
        files={"file": ("test_findings.cfg", raw, "text/plain")},
    )
    assert up.status_code == 201
    artifact_id = up.json()["artifact_id"]

    audit_r = client.post(
        "/api/v1/audits",
        json={"artifact_id": artifact_id, "device_id": "test-dev-01"},
    )
    assert audit_r.status_code == 202
    return audit_r.json()


@pytest.mark.inv("INV-05")
def test_audit_status_done(findings_audit_result: dict) -> None:
    assert findings_audit_result["status"] == "done"
    assert findings_audit_result["progress"] == 100


@pytest.mark.inv("INV-07")
def test_audit_score_two_numbers_present(findings_audit_result: dict) -> None:
    """Both score numbers must be present and non-None (INV-07)."""
    score = findings_audit_result["score"]
    assert score is not None
    assert score["verified"] is not None
    assert score["provisional_inclusive"] is not None
    assert score["provisional_dependence"] is not None


@pytest.mark.inv("INV-07")
def test_audit_score_not_blended(findings_audit_result: dict) -> None:
    """No blended field must exist in the score response (INV-07)."""
    score = findings_audit_result["score"]
    assert "blended" not in score
    assert "confidence_multiplier" not in score
    assert "discounted_score" not in score


@pytest.mark.inv("INV-05")
def test_audit_findings_present(findings_audit_result: dict) -> None:
    """All 3 seed checks must appear in the findings."""
    findings = {f["check_id"]: f for f in findings_audit_result["findings"]}
    assert "CHK-001" in findings
    assert "CHK-002" in findings
    assert "CHK-003" in findings


@pytest.mark.inv("INV-05")
def test_audit_findings_fixture_chk001_fail(findings_audit_result: dict) -> None:
    """CHK-001 (Telnet) must FAIL on the findings fixture."""
    findings = {f["check_id"]: f for f in findings_audit_result["findings"]}
    assert findings["CHK-001"]["status"] == "fail"


@pytest.mark.inv("INV-05")
def test_audit_findings_fixture_chk002_fail(findings_audit_result: dict) -> None:
    """CHK-002 (Default SNMP) must FAIL on the findings fixture."""
    findings = {f["check_id"]: f for f in findings_audit_result["findings"]}
    assert findings["CHK-002"]["status"] == "fail"


@pytest.mark.inv("INV-05")
def test_audit_findings_fixture_chk003_fail(findings_audit_result: dict) -> None:
    """CHK-003 (VTY ACL) must FAIL on the findings fixture."""
    findings = {f["check_id"]: f for f in findings_audit_result["findings"]}
    assert findings["CHK-003"]["status"] == "fail"


@pytest.mark.inv("INV-08")
def test_audit_findings_carry_trust_class(findings_audit_result: dict) -> None:
    """Every finding must carry a trust class (INV-08)."""
    for finding in findings_audit_result["findings"]:
        assert finding["trust"], f"Finding {finding['check_id']} missing trust"


# ─── Full audit flow — clean fixture ─────────────────────────────────────────

@pytest.fixture(scope="module")
def clean_audit_result(client: TestClient) -> dict:
    raw = (FIXTURES / "test_clean.cfg").read_bytes()
    up = client.post(
        "/api/v1/ingest/file",
        files={"file": ("test_clean.cfg", raw, "text/plain")},
    )
    assert up.status_code == 201
    audit_r = client.post(
        "/api/v1/audits",
        json={"artifact_id": up.json()["artifact_id"], "device_id": "test-clean-01"},
    )
    assert audit_r.status_code == 202
    return audit_r.json()


def test_clean_fixture_all_pass_via_api(clean_audit_result: dict) -> None:
    """Clean fixture must have all 3 checks passing via the full API flow."""
    findings = {f["check_id"]: f for f in clean_audit_result["findings"]}
    assert findings["CHK-001"]["status"] == "pass", "CHK-001 should pass (no telnet)"
    assert findings["CHK-002"]["status"] == "pass", "CHK-002 should pass (non-default community)"
    assert findings["CHK-003"]["status"] == "pass", "CHK-003 should pass (ACL present)"


@pytest.mark.inv("INV-13")
def test_determinism_same_artifact_same_result(client: TestClient) -> None:
    """Same artifact + device must produce identical findings (INV-13)."""
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    up = client.post(
        "/api/v1/ingest/file",
        files={"file": ("det.cfg", raw, "text/plain")},
    )
    artifact_id = up.json()["artifact_id"]

    r1 = client.post("/api/v1/audits", json={"artifact_id": artifact_id, "device_id": "det-dev"})
    r2 = client.post("/api/v1/audits", json={"artifact_id": artifact_id, "device_id": "det-dev"})

    f1 = {f["check_id"]: f["status"] for f in r1.json()["findings"]}
    f2 = {f["check_id"]: f["status"] for f in r2.json()["findings"]}
    assert f1 == f2


# ─── Job polling ──────────────────────────────────────────────────────────────

def test_get_audit_job(client: TestClient) -> None:
    """GET /audits/{job_id} must return the same result as the POST."""
    raw = (FIXTURES / "test_findings.cfg").read_bytes()
    up = client.post(
        "/api/v1/ingest/file",
        files={"file": ("poll.cfg", raw, "text/plain")},
    )
    job_id = client.post(
        "/api/v1/audits",
        json={"artifact_id": up.json()["artifact_id"], "device_id": "poll-dev"},
    ).json()["job_id"]

    r = client.get(f"/api/v1/audits/{job_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "done"


def test_get_missing_job_returns_404(client: TestClient) -> None:
    r = client.get("/api/v1/audits/nonexistent-job-id")
    assert r.status_code == 404


# ─── OpenAPI schema ───────────────────────────────────────────────────────────

def test_openapi_schema_exportable(client: TestClient) -> None:
    """OpenAPI schema must be exportable (Phase 1 exit gate)."""
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"] == "PRAMANA"
    assert "/api/v1/ingest/file" in schema["paths"]
    assert "/api/v1/audits" in schema["paths"]
    assert "/api/v1/audits/{job_id}" in schema["paths"]


@pytest.mark.inv("INV-07")
def test_openapi_score_schema_no_blended_field(client: TestClient) -> None:
    """TwoNumberScore schema must not contain forbidden field NAMES (INV-07).

    We check JSON property keys, not description text (descriptions may legitimately
    explain what the system does NOT do).
    """
    r = client.get("/api/openapi.json")
    schema = r.json()
    schemas = schema.get("components", {}).get("schemas", {})
    two_num = schemas.get("TwoNumberScore", {})
    properties = two_num.get("properties", {}).keys()

    forbidden = {"blended", "confidence_multiplier", "discounted_score"}
    violations = forbidden & set(properties)
    assert not violations, f"Forbidden field names in TwoNumberScore: {violations}"
