from __future__ import annotations

import hashlib
import io
import json
import time
from contextlib import redirect_stderr, redirect_stdout
from typing import TYPE_CHECKING

from TIPCommon.encryption import decrypt, encrypt

from .constants import (
    GLOBAL_CONTEXT_SCOPE,
    INTEGRATION_NAME,
    TOKEN_CACHE_PROPERTY_KEY,
    TOKEN_EXPIRY_BUFFER_SECONDS,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.types import ChronicleSOAR, SingleJson


def _invoke(fn: Callable[..., object], positional: tuple[object, ...], named: SingleJson) -> object:
    try:
        return fn(*positional)
    except TypeError:
        return fn(**named)


def _credential_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def encrypt_context_value(payload: str, secret: str) -> str:
    """Encrypt a token-cache payload using TIPCommon AES-GCM encryption."""
    return encrypt(payload, secret).decode()


def decrypt_context_value(raw: str, secret: str) -> str:
    """Decrypt a token-cache payload using TIPCommon AES-GCM encryption."""
    return decrypt(raw.encode(), secret)


class TokenCache:
    """In-process plus SOAR-context cache for v2 OAuth access tokens."""

    def __init__(
        self,
        siemplify: ChronicleSOAR | None = None,
        now: Callable[[], float] | None = None,
        *,
        use_context: bool = True,
        secret: str | None = None,
    ) -> None:
        """Initialize the cache, optionally backed by SOAR context.

        Args:
            siemplify: Optional SOAR SDK object used to persist tokens.
            now: Optional clock used for expiry checks. Defaults to time.time.
            use_context: When False, skip SOAR context reads and writes.
            secret: Client credentials used to encrypt tokens and bind the cache.
        """
        self.siemplify = siemplify if use_context else None
        self._now = now or time.time
        self._memory: SingleJson | None = None
        self._secret: str | None = None
        self._credential_hash: str | None = None
        if secret:
            self.bind_secret(secret)

    def bind_secret(self, secret: str) -> None:
        """Bind the cache to client credentials used for encryption and freshness."""
        self._secret = secret
        self._credential_hash = _credential_hash(secret)

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
        if self._credential_hash:
            record["credential_hash"] = self._credential_hash
        self._memory = record
        self._write_context(record)

    def invalidate(self) -> None:
        """Clear the in-memory token and any persisted SOAR context value."""
        self._memory = None
        self._write_context(None)

    def _is_fresh(self, record: SingleJson | None) -> bool:
        if not record or not record.get("access_token") or not record.get("expires_at"):
            return False
        if self._credential_hash and record.get("credential_hash") != self._credential_hash:
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
            payload = self._decrypt_payload(raw)
            data = json.loads(payload) if isinstance(payload, str) else payload
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def _write_context(self, record: SingleJson | None) -> None:
        value = "" if record is None else self._encrypt_payload(json.dumps(record))
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

    def _encrypt_payload(self, payload: str) -> str:
        if not self._secret:
            return payload
        return encrypt_context_value(payload, self._secret)

    def _decrypt_payload(self, raw: object) -> object:
        if not self._secret:
            return raw
        if not isinstance(raw, str):
            raise ValueError("Encrypted token cache value must be a string")
        return decrypt_context_value(raw, self._secret)

    def _call_context(self, method_names: tuple[str, ...], positional: tuple[object, ...], named: SingleJson) -> object:
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
                except Exception as exc:
                    logger: object = getattr(self.siemplify, "LOGGER", None)
                    warn: object = getattr(logger, "warn", None) or getattr(logger, "warning", None)
                    if callable(warn):
                        warn(f"Failed to access Doppel OAuth token context via {name}: {exc}")
                    continue
        return None
