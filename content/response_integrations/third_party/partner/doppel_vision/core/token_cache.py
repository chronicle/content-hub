from __future__ import annotations

import io
import json
import time
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from .constants import (
    GLOBAL_CONTEXT_SCOPE,
    INTEGRATION_NAME,
    TOKEN_CACHE_PROPERTY_KEY,
    TOKEN_EXPIRY_BUFFER_SECONDS,
)


def _invoke(fn: Any, positional: tuple[Any, ...], named: dict[str, Any]) -> Any:
    try:
        return fn(*positional)
    except TypeError:
        return fn(**named)


class TokenCache:
    """In-process plus SOAR-context cache for v2 OAuth access tokens."""

    def __init__(
        self,
        siemplify: Any | None = None,
        now: Any | None = None,
        *,
        use_context: bool = True,
    ) -> None:
        self.siemplify = siemplify if use_context else None
        self._now = now or time.time
        self._memory: dict[str, Any] | None = None

    def _identifier(self) -> str:
        identifier = getattr(self.siemplify, "integration_instance", None)
        if identifier:
            return str(identifier)
        return INTEGRATION_NAME

    def get_token(self) -> str | None:
        cached = self._memory if self._is_fresh(self._memory) else None
        if cached:
            return cached["access_token"]

        stored = self._read_context()
        if self._is_fresh(stored):
            self._memory = stored
            return stored["access_token"]
        return None

    def set_token(self, access_token: str, expires_in: int) -> None:
        record = {
            "access_token": access_token,
            "expires_at": self._now() + expires_in,
        }
        self._memory = record
        self._write_context(record)

    def invalidate(self) -> None:
        self._memory = None
        self._write_context(None)

    def _is_fresh(self, record: dict[str, Any] | None) -> bool:
        if not record or not record.get("access_token") or not record.get("expires_at"):
            return False
        return self._now() < float(record["expires_at"]) - TOKEN_EXPIRY_BUFFER_SECONDS

    def _read_context(self) -> dict[str, Any] | None:
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

    def _write_context(self, record: dict[str, Any] | None) -> None:
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
        positional: tuple[Any, ...],
        named: dict[str, Any],
    ) -> Any:
        if self.siemplify is None:
            return None
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            for name in method_names:
                fn = getattr(self.siemplify, name, None)
                if not callable(fn):
                    continue
                try:
                    return _invoke(fn, positional, named)
                except Exception:
                    continue
        return None
