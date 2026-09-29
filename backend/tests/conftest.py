"""
No-egress fixture (INV-11).

Autouse session-scoped fixture that blocks:
  - socket.connect() to non-loopback addresses
  - socket.getaddrinfo() for external hostnames

All tests inherit this automatically. To test network code (e.g. the egress check
itself), override by requesting the `allow_egress` fixture.
"""
from __future__ import annotations

import socket
import pytest


_LOOPBACK_PREFIXES = ("127.", "::1", "localhost")

_original_connect = socket.socket.connect
_original_getaddrinfo = socket.getaddrinfo


def _is_loopback(address: object) -> bool:
    """Return True if *address* is a loopback or Unix socket path."""
    if isinstance(address, str):
        # Unix domain socket
        return True
    if isinstance(address, (tuple, list)) and len(address) >= 1:
        host = str(address[0])
        return any(host.startswith(p) for p in _LOOPBACK_PREFIXES)
    return False


def _blocking_connect(self: socket.socket, address: object) -> None:
    if not _is_loopback(address):
        raise OSError(
            f"[no-egress fixture] Attempted non-loopback socket.connect({address!r}). "
            "Tests must not make external network calls (INV-11)."
        )
    _original_connect(self, address)


def _blocking_getaddrinfo(
    host: object,
    port: object,
    *args: object,
    **kwargs: object,
) -> object:
    if not _is_loopback(host):
        raise OSError(
            f"[no-egress fixture] Attempted socket.getaddrinfo({host!r}, {port!r}). "
            "Tests must not resolve external hostnames (INV-11)."
        )
    return _original_getaddrinfo(host, port, *args, **kwargs)


@pytest.fixture(autouse=True, scope="function")
def block_egress(request: pytest.FixtureRequest) -> None:  # type: ignore[type-arg]
    """Function-scoped autouse: block all non-loopback network calls (INV-11)."""
    if "allow_egress" in request.fixturenames:
        yield
        return
    socket.socket.connect = _blocking_connect  # type: ignore[method-assign]
    socket.getaddrinfo = _blocking_getaddrinfo  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = _original_connect  # type: ignore[method-assign]
        socket.getaddrinfo = _original_getaddrinfo  # type: ignore[assignment]


@pytest.fixture
def allow_egress() -> None:
    """Request this fixture in a test to bypass the egress block."""
    yield  # noqa: PT022
