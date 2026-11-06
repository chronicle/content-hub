from __future__ import annotations

import io
import json
import time
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR, SingleJson

from .constants import (
    GLOBAL_CONTEXT_SCOPE,
    INTEGRATION_NAME,
    TOKEN_CACHE_PROPERTY_KEY,
    TOKEN_EXPIRY_BUFFER_SECONDS,
)


def _invoke(fn: Callable[..., object], positional: tuple[object, ...], named: SingleJson) -> object:
    try:
        return fn(*positional)
    except TypeError:
        return fn(**named)


class TokenCache:
    """In-process plus SOAR-context cache for v2 OAuth access tokens."""

    def __init__(
        self, siemplify: ChronicleSOAR | None = None, now: Callable[[], float] | None = None, use_context: bool = True
    ) -> None:
        """Initialize the cache, optionally backed by SOAR context.

        Args:
            siemplify: Optional SOAR SDK object used to persist tokens.
            now: Optional clock used for expiry checks. Defaults to time.time.
            use_context: When False, skip SOAR context reads and writes.
        """
        self.siemplify = siemplify if use_context else None
        self._now = now or time.time
        self._memory: SingleJson | None = None

    def _identifier(self) -> str:
        identifier: object = getattr(self.siemplify, "integration_instance", None)
        if identifier:
            return str(identifier)
        return INTEGRATION_NAME

    def get_token(self) -> str | None:
        """Return a cached access token when it is still valid.

        Returns:
            The access token, or None when no fresh token is available.
        """
        cached = self._memory if self._is_fresh(self._memory) else None
        if cached:
            return str(cached["access_token"])

        stored = self._read_context()
        if self._is_fresh(stored):
            self._memory = stored
            return str(stored["access_token"])
        return None

    def set_token(self, access_token: str, expires_in: int) -> None:
        """Store an access token in memory and, when available, SOAR context.

        Args:
            access_token: OAuth access token.
            expires_in: Token lifetime in seconds.
        """
        record: SingleJson = {
            "access_token": access_token,
            "expires_at": self._now() + expires_in,
        }
        self._memory = record
        self._write_context(record)

    def invalidate(self) -> None:
        """Clear the in-memory token and any persisted SOAR context value."""
        self._memory = None
        self._write_context(None)

    def _is_fresh(self, record: SingleJson | None) -> bool:
        if not record or not record.get("access_token") or not record.get("expires_at"):
            return False
        return self._now() < float(record["expires_at"]) - TOKEN_EXPIRY_BUFFER_SECONDS

    def _read_context(self) -> SingleJson | None:
        raw = self._call_context(
            ("get_context_property",),
            (GLOBAL_CONTEXT_SCOPE, self._identifier(), TOKEN_CACHE_PROPERTY_KEY),
            {
                "context_type": GLOBAL_CONTEXT_SCOPE,
                "identifier": self._identifier(),
                "property_key": TOKEN_CACHE_PROPERTY_KEY,
            },
        )
        if not raw:
            return None
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def _write_context(self, record: SingleJson | None) -> None:
        value = "" if record is None else json.dumps(record)
        self._call_context(
            ("try_set_context_property", "set_context_property"),
            (
                GLOBAL_CONTEXT_SCOPE,
                self._identifier(),
                TOKEN_CACHE_PROPERTY_KEY,
                value,
            ),
            {
                "context_type": GLOBAL_CONTEXT_SCOPE,
                "identifier": self._identifier(),
                "property_key": TOKEN_CACHE_PROPERTY_KEY,
                "property_value": value,
            },
        )

    def _call_context(
        self,
        method_names: tuple[str, ...],
        positional: tuple[object, ...],
        named: SingleJson,
    ) -> object:
        if self.siemplify is None:
            return None
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            for name in method_names:
                fn: object = getattr(self.siemplify, name, None)
                if not callable(fn):
                    continue
                try:
                    return _invoke(fn, positional, named)
                except Exception:
                    continue
        return None
