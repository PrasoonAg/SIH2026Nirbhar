"""
bootstrap.settings — application settings via pydantic-settings.

All configuration is injected through environment variables (12-factor).
No secrets in source code.
"""
from __future__ import annotations

from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """PRAMANA application settings."""

    model_config = SettingsConfigDict(
        env_prefix="PRAMANA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    db_url: str = "sqlite+aiosqlite:///./data/pramana.db"

    # ── Paths ─────────────────────────────────────────────────────────────────
    data_dir: Path = Path("./data")
    models_dir: Path = Path("./models")

    # ── Security ──────────────────────────────────────────────────────────────
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    session_max_age_seconds: int = 3600
    login_rate_limit_per_minute: int = 5

    # ── Offline / model flags ─────────────────────────────────────────────────
    hf_hub_offline: bool = True
    transformers_offline: bool = True

    # ── Audit limits (INV-11 / §12) ───────────────────────────────────────────
    zip_max_members: int = 1000
    zip_max_total_bytes: int = 500 * 1024 * 1024   # 500 MB
    zip_max_member_bytes: int = 50 * 1024 * 1024    # 50 MB
    zip_max_compression_ratio: float = 100.0
    parse_time_budget_seconds: float = 30.0

    # ── Gate thresholds (placeholders — calibrated in Phase 5) ────────────────
    lexical_top_k: int = 5
    lexical_min_score: float = 0.1
    second_model_min_score: float = 0.5
    tau_conf: float = 0.5   # proposer confidence threshold for Ollama fallback

    @field_validator("data_dir", "models_dir", mode="before")
    @classmethod
    def _expand_paths(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()
