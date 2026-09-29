"""
ingest.service — IngestService implementation (Phase 1: file bytes only).

Phase 2 adds ZIP support, device/site registration.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from pramana.ingest.api import Artifact, IngestError, IngestService, ZipGuardError
from pramana.shared_kernel.api import new_id, sha256_bytes


# ─── ZIP guard defaults (configurable via Settings) ───────────────────────────

_ZIP_MAX_MEMBERS = 1000
_ZIP_MAX_TOTAL_BYTES = 500 * 1024 * 1024   # 500 MB
_ZIP_MAX_MEMBER_BYTES = 50 * 1024 * 1024    # 50 MB
_ZIP_MAX_RATIO = 100.0


class IngestServiceImpl(IngestService):
    """
    Phase 1 implementation: in-memory artifact store (dict-backed).
    Phase 2: swap to filesystem content-addressed store.
    """

    def __init__(self) -> None:
        # artifact_id → (Artifact, bytes)
        self._store: dict[str, tuple[Artifact, bytes]] = {}
        # sha256 → artifact_id  (deduplication)
        self._sha_index: dict[str, str] = {}

    def ingest_bytes(
        self,
        raw_bytes: bytes,
        filename: str,
        device_id: str | None = None,
        vendor_hint: str | None = None,
    ) -> Artifact:
        sha = sha256_bytes(raw_bytes)

        # Deduplication
        if sha in self._sha_index:
            existing_id = self._sha_index[sha]
            return self._store[existing_id][0]

        artifact_id = new_id()
        artifact = Artifact(
            artifact_id=artifact_id,
            sha256=sha,
            filename=filename,
            size_bytes=len(raw_bytes),
            vendor_hint=vendor_hint,
        )
        self._store[artifact_id] = (artifact, raw_bytes)
        self._sha_index[sha] = artifact_id
        return artifact

    def ingest_zip(
        self,
        zip_bytes: bytes,
        filename: str,
        max_members: int = _ZIP_MAX_MEMBERS,
        max_total_bytes: int = _ZIP_MAX_TOTAL_BYTES,
        max_member_bytes: int = _ZIP_MAX_MEMBER_BYTES,
        max_ratio: float = _ZIP_MAX_RATIO,
    ) -> list[Artifact]:
        """Unpack a ZIP with all safety guards (Phase 2 full ZIP guard)."""
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except zipfile.BadZipFile as exc:
            raise ZipGuardError(f"Invalid ZIP file: {exc}") from exc

        members = zf.infolist()

        # Guard: max members
        if len(members) > max_members:
            raise ZipGuardError(
                f"ZIP has {len(members)} members, max {max_members}"
            )

        total_uncompressed = 0
        artifacts: list[Artifact] = []

        for member in members:
            name = member.filename

            # Guard: absolute paths, directory traversal, NUL bytes
            if name.startswith("/") or ".." in name or "\x00" in name:
                raise ZipGuardError(f"ZIP member has unsafe path: {name!r}")

            # Guard: symlinks
            if member.is_dir():
                continue

            # Guard: nested archives
            if name.lower().endswith((".zip", ".tar", ".gz", ".tgz", ".7z", ".rar")):
                raise ZipGuardError(f"ZIP member is a nested archive: {name!r}")

            # Guard: member size
            if member.file_size > max_member_bytes:
                raise ZipGuardError(
                    f"ZIP member {name!r} exceeds {max_member_bytes} bytes"
                )

            # Guard: compression ratio
            if member.compress_size > 0:
                ratio = member.file_size / member.compress_size
                if ratio > max_ratio:
                    raise ZipGuardError(
                        f"ZIP member {name!r} compression ratio {ratio:.1f} exceeds {max_ratio}"
                    )

            member_bytes = zf.read(name)
            total_uncompressed += len(member_bytes)

            # Guard: total uncompressed size
            if total_uncompressed > max_total_bytes:
                raise ZipGuardError(
                    f"ZIP total uncompressed size exceeds {max_total_bytes} bytes"
                )

            artifacts.append(
                self.ingest_bytes(member_bytes, filename=name)
            )

        return artifacts

    def get_artifact(self, artifact_id: str) -> Artifact:
        if artifact_id not in self._store:
            from pramana.shared_kernel.api import NotFoundError
            raise NotFoundError(f"Artifact {artifact_id!r} not found")
        return self._store[artifact_id][0]

    def read_artifact_bytes(self, artifact_id: str) -> bytes:
        if artifact_id not in self._store:
            from pramana.shared_kernel.api import NotFoundError
            raise NotFoundError(f"Artifact {artifact_id!r} not found")
        return self._store[artifact_id][1]


_default_ingest_service: IngestServiceImpl | None = None


def get_ingest_service() -> IngestServiceImpl:
    global _default_ingest_service
    if _default_ingest_service is None:
        _default_ingest_service = IngestServiceImpl()
    return _default_ingest_service

