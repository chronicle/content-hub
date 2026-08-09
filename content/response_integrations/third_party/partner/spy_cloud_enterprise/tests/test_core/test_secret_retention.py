"""Tests for the connector's optional plaintext-secret retention.

Secret retention is gated by the ``include_secrets`` flag the connector derives
from its "Include Plaintext Secrets" option. Off (the default) preserves the
historical behavior of stripping secrets before anything is persisted; on carries
the raw values into the UDM extensions so the parser can flatten them onto the
case event.
"""
from __future__ import annotations

from spy_cloud_enterprise.core.spycloud_udm_converter import SpyCloudUdmConverter


def _record() -> dict:
    return {
        "source_id": 123,
        "severity": 20,
        "email": "victim@example.com",
        "password_type": "plaintext",
        "password_plaintext": "hunter2",
        "password": "hashed-xyz",
        "cookies": "session=abc",
    }


class TestSecretRetention:
    def test_default_strips_secrets_from_extensions(self) -> None:
        converter = SpyCloudUdmConverter()
        event = converter.convert_record(_record())
        extensions = event.get("extensions", {})

        assert "password_plaintext" not in extensions
        assert "password" not in extensions
        assert "cookies" not in extensions
        # Presence booleans are still derived.
        assert event.get("additional", {}).get("has_plaintext_password") is True

    def test_default_keeps_no_secret_value_anywhere(self) -> None:
        converter = SpyCloudUdmConverter()
        event = converter.convert_record(_record())
        import json

        assert "hunter2" not in json.dumps(event)

    def test_include_secrets_carries_values_into_extensions(self) -> None:
        converter = SpyCloudUdmConverter(include_secrets=True)
        event = converter.convert_record(_record())
        extensions = event.get("extensions", {})

        assert extensions.get("password_plaintext") == "hunter2"
        assert extensions.get("password") == "hashed-xyz"
        assert extensions.get("cookies") == "session=abc"
        # Presence booleans are still derived alongside the raw values.
        assert event.get("additional", {}).get("has_plaintext_password") is True
