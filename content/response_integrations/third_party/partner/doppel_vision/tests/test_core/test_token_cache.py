from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from core.auth_provider_v2 import AuthProviderV2
from core.constants import TOKEN_CACHE_PROPERTY_KEY
from core.token_cache import TokenCache


class ContextStore:
    """Minimal SOAR context stand-in shared across simulated playbook processes."""

    def __init__(self, instance: str = "instance-1") -> None:
        self.integration_instance = instance
        self.store: dict[tuple[object, ...], str] = {}

    def get_context_property(self, context_type, identifier, property_key):
        return self.store.get((context_type, identifier, property_key))

    def try_set_context_property(self, context_type, identifier, property_key, property_value):
        self.store[(context_type, identifier, property_key)] = property_value


class SetOnlyContextStore:
    def __init__(self, instance: str = "instance-1") -> None:
        self.integration_instance = instance
        self.store: dict[tuple[object, ...], str] = {}

    def get_context_property(self, context_type, identifier, property_key):
        return self.store.get((context_type, identifier, property_key))

    def set_context_property(self, context_type, identifier, property_key, property_value):
        self.store[(context_type, identifier, property_key)] = property_value


def test_token_cache_uses_memory_then_context() -> None:
    siemplify = MagicMock()
    siemplify.integration_instance = "instance-1"
    siemplify.get_context_property.return_value = json.dumps(
        {"access_token": "ctx-token", "expires_at": 10_000},
    )
    cache = TokenCache(siemplify=siemplify, now=lambda: 1_000)
    assert cache.get_token() == "ctx-token"

    cache.set_token("mem-token", 86400)
    siemplify.try_set_context_property.assert_called()
    assert TOKEN_CACHE_PROPERTY_KEY in siemplify.try_set_context_property.call_args[0]
    assert cache.get_token() == "mem-token"
    siemplify.get_context_property.reset_mock()
    cache.get_token()
    siemplify.get_context_property.assert_not_called()


def test_token_cache_expires_with_buffer() -> None:
    cache = TokenCache(now=lambda: 1_000)
    cache.set_token("tok", 200)
    assert cache.get_token() is None


def test_token_cache_invalidate_clears_context() -> None:
    siemplify = MagicMock()
    siemplify.integration_instance = "instance-1"
    cache = TokenCache(siemplify=siemplify, now=lambda: 1_000)
    cache.set_token("tok", 86400)
    cache.invalidate()
    assert cache.get_token() is None
    assert siemplify.try_set_context_property.call_args[0][-1] == ""


def test_token_cache_skips_context_when_disabled() -> None:
    siemplify = MagicMock()
    cache = TokenCache(siemplify=siemplify, now=lambda: 1_000, use_context=False)
    cache.set_token("tok", 86400)
    assert cache.get_token() == "tok"
    siemplify.get_context_property.assert_not_called()
    siemplify.set_context_property.assert_not_called()
    siemplify.try_set_context_property.assert_not_called()


def test_token_cache_falls_back_to_set_context_property() -> None:
    siemplify = SetOnlyContextStore()
    writer = TokenCache(siemplify=siemplify, now=lambda: 1_000)
    writer.set_token("tok-1", 86400)
    reader = TokenCache(siemplify=siemplify, now=lambda: 1_100)
    assert reader.get_token() == "tok-1"


def test_token_reused_across_new_cache_instances() -> None:
    siemplify = ContextStore()
    first = TokenCache(siemplify=siemplify, now=lambda: 1_000)
    first.set_token("tok-1", 86400)
    second = TokenCache(siemplify=siemplify, now=lambda: 1_100)
    assert second.get_token() == "tok-1"


def test_token_cache_survives_missing_context_property() -> None:
    siemplify = MagicMock()
    siemplify.integration_instance = "instance-1"
    siemplify.get_context_property.side_effect = Exception("property not found")
    siemplify.try_set_context_property.side_effect = Exception("cannot set")
    cache = TokenCache(siemplify=siemplify, now=lambda: 1_000)
    assert cache.get_token() is None
    cache.set_token("tok", 86400)
    assert cache.get_token() == "tok"


def test_v2_auth_reuses_token_across_playbook_runs() -> None:
    store = ContextStore()
    session = MagicMock()
    session.post.return_value = MagicMock(
        ok=True,
        status_code=200,
        content=b"{}",
        json=lambda: {"access_token": "tok-1", "expires_in": 86400},
    )
    first = AuthProviderV2(
        "id",
        "secret",
        token_cache=TokenCache(siemplify=store, now=lambda: 1_000),
        session=session,
    )
    assert first.get_auth_headers()["Authorization"] == "Bearer tok-1"
    session.post.assert_called_once()
    session.post.reset_mock()

    second = AuthProviderV2(
        "id",
        "secret",
        token_cache=TokenCache(siemplify=store, now=lambda: 1_100),
        session=session,
    )
    assert second.get_auth_headers()["Authorization"] == "Bearer tok-1"
    session.post.assert_not_called()


def test_ping_does_not_disable_token_persist() -> None:
    source = (Path(__file__).resolve().parents[2] / "actions" / "Ping.py").read_text(
        encoding="utf-8",
    )
    assert "persist_token=False" not in source
