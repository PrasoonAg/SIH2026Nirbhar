"""
bootstrap.api — Public surface stub for the bootstrap module.

Composition root: creates the FastAPI application instance.
Real implementation is in bootstrap.main.
"""
from __future__ import annotations

from typing import Protocol


class AppFactory(Protocol):
    """Protocol for application factory functions."""

    def __call__(self) -> object:  # FastAPI
        ...


def create_app() -> object:
    """Import and return the application. Avoids circular imports at test time."""
    from pramana.bootstrap.main import create_application  # noqa: PLC0415
    return create_application()
