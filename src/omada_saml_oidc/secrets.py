"""Persistent secret generation for the bridge runtime."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
import secrets


def ensure_persisted_secret(path: Path, *, provided: str | None = None, size: int = 32) -> str:
    """Create a stable high-entropy text secret at the given path.

    Args:
        path: File path where the secret should be stored.
        provided: Optional caller-provided value to persist when the file does
            not already exist.
        size: Entropy size passed to ``secrets.token_urlsafe``.

    Returns:
        The persisted secret text.
    """

    if path.exists():
        return path.read_text().strip()

    path.parent.mkdir(parents=True, exist_ok=True)
    value = provided.strip() if provided else secrets.token_urlsafe(size)
    path.write_text(value + "\n")
    with suppress(OSError):
        path.chmod(0o600)
    return value
