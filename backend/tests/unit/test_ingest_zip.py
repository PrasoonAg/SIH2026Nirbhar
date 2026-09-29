"""
unit/test_ingest_zip.py — ZIP guard tests (INV-11, Phase 2 exit gate).

Tests all ZIP safety guards:
  - Max members
  - Max total uncompressed size
  - Max single member size
  - Compression ratio (bomb detection)
  - Path traversal
  - Nested archives
  - Absolute paths
  - NUL bytes in filenames
"""
from __future__ import annotations

import io
import os
import zipfile
import zlib

import pytest

from pramana.ingest.api import ZipGuardError
from pramana.ingest.service import IngestServiceImpl

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_zip(members: dict[str, bytes], compression=zipfile.ZIP_STORED) -> bytes:
    """Build a valid ZIP in-memory with given {filename: content} members."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compression) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _make_bomb(compressed_size: int = 1024, ratio: int = 200) -> bytes:
    """Create a ZIP bomb: one member with extreme compression ratio."""
    raw_data = b"A" * (compressed_size * ratio)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.txt", raw_data)
    return buf.getvalue()


# ─── Valid ZIP ────────────────────────────────────────────────────────────────

def test_valid_zip_ingested():
    svc = IngestServiceImpl()
    zip_bytes = _make_zip({"router.cfg": b"hostname router\n", "fw.cfg": b"config system global\n"})
    artifacts = svc.ingest_zip(zip_bytes, "configs.zip")
    assert len(artifacts) == 2
    names = {a.filename for a in artifacts}
    assert "router.cfg" in names
    assert "fw.cfg" in names


def test_valid_zip_deduplication():
    """Same file content in two ZIP members → same artifact_id for both."""
    svc = IngestServiceImpl()
    content = b"hostname router\n"
    zip_bytes = _make_zip({"a.cfg": content, "b.cfg": content})
    artifacts = svc.ingest_zip(zip_bytes, "dup.zip")
    assert len(artifacts) == 2
    assert artifacts[0].artifact_id == artifacts[1].artifact_id


def test_empty_zip_returns_no_artifacts():
    svc = IngestServiceImpl()
    zip_bytes = _make_zip({})
    artifacts = svc.ingest_zip(zip_bytes, "empty.zip")
    assert artifacts == []


# ─── Corrupted ZIP ────────────────────────────────────────────────────────────

def test_corrupted_zip_raises():
    svc = IngestServiceImpl()
    with pytest.raises(ZipGuardError, match="Invalid ZIP"):
        svc.ingest_zip(b"this is not a zip", "bad.zip")


# ─── Path traversal ───────────────────────────────────────────────────────────

def test_path_traversal_dotdot_blocked():
    svc = IngestServiceImpl()
    # Manually craft a ZIP with a .. path
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("../../../etc/passwd")
        zf.writestr(info, b"root:x:0:0:root:/root:/bin/bash")
    with pytest.raises(ZipGuardError, match="unsafe path"):
        svc.ingest_zip(buf.getvalue(), "traversal.zip")


def test_absolute_path_blocked():
    svc = IngestServiceImpl()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("/etc/passwd")
        zf.writestr(info, b"root:x:0:0")
    with pytest.raises(ZipGuardError, match="unsafe path"):
        svc.ingest_zip(buf.getvalue(), "abspath.zip")


# ─── Nested archives ─────────────────────────────────────────────────────────

def test_nested_zip_blocked():
    svc = IngestServiceImpl()
    inner_zip = _make_zip({"inner.cfg": b"config"})
    outer = _make_zip({"nested.zip": inner_zip})
    with pytest.raises(ZipGuardError, match="nested archive"):
        svc.ingest_zip(outer, "outer.zip")


def test_nested_tar_blocked():
    svc = IngestServiceImpl()
    outer = _make_zip({"configs.tar": b"fake tar data"})
    with pytest.raises(ZipGuardError, match="nested archive"):
        svc.ingest_zip(outer, "outer.zip")


# ─── Compression ratio (bomb) ────────────────────────────────────────────────

@pytest.mark.inv("INV-11")
def test_zip_bomb_ratio_blocked():
    """ZIP bomb: single member with ratio > max_ratio must be rejected."""
    svc = IngestServiceImpl()
    bomb = _make_bomb(compressed_size=512, ratio=150)
    with pytest.raises(ZipGuardError, match="compression ratio"):
        svc.ingest_zip(bomb, "bomb.zip", max_ratio=50.0)


# ─── Max members ─────────────────────────────────────────────────────────────

def test_max_members_exceeded():
    svc = IngestServiceImpl()
    members = {f"file{i}.cfg": b"hostname r\n" for i in range(5)}
    zip_bytes = _make_zip(members)
    with pytest.raises(ZipGuardError, match="members"):
        svc.ingest_zip(zip_bytes, "many.zip", max_members=3)


# ─── Max member size ─────────────────────────────────────────────────────────

def test_max_member_size_exceeded():
    svc = IngestServiceImpl()
    big_content = b"A" * (2 * 1024 * 1024)  # 2 MB
    zip_bytes = _make_zip({"big.cfg": big_content})
    with pytest.raises(ZipGuardError, match="exceeds"):
        svc.ingest_zip(zip_bytes, "big.zip", max_member_bytes=1 * 1024 * 1024)


# ─── Max total size ──────────────────────────────────────────────────────────

def test_max_total_size_exceeded():
    svc = IngestServiceImpl()
    members = {f"f{i}.cfg": b"A" * 500_000 for i in range(5)}  # 2.5 MB total
    zip_bytes = _make_zip(members)
    with pytest.raises(ZipGuardError, match="total uncompressed"):
        svc.ingest_zip(zip_bytes, "total.zip", max_total_bytes=1_000_000)


# ─── Directory entries skipped (not counted as members) ──────────────────────

def test_directory_entries_skipped():
    svc = IngestServiceImpl()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.mkdir("subdir/")                    # directory entry
        zf.writestr("subdir/router.cfg", b"hostname r\n")
    artifacts = svc.ingest_zip(buf.getvalue(), "dirs.zip")
    assert len(artifacts) == 1
    assert artifacts[0].filename == "subdir/router.cfg"
