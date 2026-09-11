"""Tests for the SpyCloud Enterprise Filter Passwords By Policy action.

The action reads the plaintext password values the connector flattened onto the
case events and reports how many still match a minimum-length / symbol policy, so
the Entra ID response playbook can gate a password reset. It makes no SpyCloud API
call, so these tests inject a fake case object rather than mocking the vendor SDK.
"""

from __future__ import annotations

import dataclasses
from typing import Any
from unittest.mock import MagicMock, patch

from spy_cloud_enterprise.actions import FilterPasswordsByPolicy


@dataclasses.dataclass
class _Event:
    additional_properties: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class _Alert:
    name: str = ""
    security_events: list = dataclasses.field(default_factory=list)


def _event(**extra: Any) -> _Event:
    props = {
        "device_vendor": "SpyCloud",
        "spycloud_email": "victim@example.com",
    }
    props.update(extra)
    return _Event(additional_properties=props)


def _make_siemplify(
    alerts: list[_Alert],
    params: dict[str, Any] | None = None,
) -> tuple[MagicMock, list[dict[str, Any]]]:
    """Build a SiemplifyAction double whose case exposes the given alerts."""
    params = params or {}
    siemplify = MagicMock(name="SiemplifyAction")
    siemplify.case.alerts = alerts
    siemplify.case_id = "1234"
    siemplify.result = MagicMock(name="result")

    def _extract(param_name: str, default_value: Any = None, **_: Any) -> Any:
        return params.get(param_name, default_value)

    siemplify.extract_action_param.side_effect = _extract

    end_calls: list[dict[str, Any]] = []

    def _end(message: str = "", result_value: Any = None, status: Any = None) -> None:
        end_calls.append(
            {"message": message, "result_value": result_value, "status": status}
        )

    siemplify.end.side_effect = _end
    return siemplify, end_calls


def _run(siemplify: MagicMock) -> None:
    with patch.object(FilterPasswordsByPolicy, "SiemplifyAction", return_value=siemplify):
        FilterPasswordsByPolicy.main()


def _json(siemplify: MagicMock) -> dict[str, Any]:
    return siemplify.result.add_result_json.call_args.args[0]


class TestFilterPasswordsByPolicy:
    def test_keeps_policy_conforming_password(self) -> None:
        """A long password with a symbol survives the default policy."""
        alerts = [_Alert("SpyCloud", [_event(spycloud_password_plaintext="Sup3r$ecret")])]
        siemplify, end_calls = _make_siemplify(alerts)

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1
        assert _json(siemplify)["remaining"] == 1

    def test_drops_short_password(self) -> None:
        """A password shorter than the minimum length is dropped."""
        alerts = [_Alert("SpyCloud", [_event(spycloud_password_plaintext="a$1")])]
        siemplify, end_calls = _make_siemplify(alerts)

        _run(siemplify)

        assert end_calls[0]["result_value"] == 0
        payload = _json(siemplify)
        assert payload["remaining"] == 0
        assert payload["dropped"] == 1

    def test_drops_password_missing_symbol_when_required(self) -> None:
        alerts = [_Alert("SpyCloud", [_event(spycloud_password_plaintext="longenough12")])]
        siemplify, end_calls = _make_siemplify(alerts)

        _run(siemplify)

        assert end_calls[0]["result_value"] == 0

    def test_require_symbol_false_keeps_symbolless_password(self) -> None:
        alerts = [_Alert("SpyCloud", [_event(spycloud_password_plaintext="longenough12")])]
        siemplify, end_calls = _make_siemplify(alerts, params={"Require Symbol": False})

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1

    def test_custom_minimum_length(self) -> None:
        alerts = [_Alert("SpyCloud", [_event(spycloud_password_plaintext="ab$")])]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Minimum Password Length": 3}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1

    def test_no_passwords_present_completes_with_message(self) -> None:
        """With secret retention off, no password values are on the events."""
        alerts = [_Alert("SpyCloud", [_event(spycloud_has_plaintext_password="true")])]
        siemplify, end_calls = _make_siemplify(alerts)

        _run(siemplify)

        assert end_calls[0]["result_value"] == 0
        assert "No plaintext passwords" in end_calls[0]["message"]

    def test_never_surfaces_plaintext_in_json(self) -> None:
        """The JSON result masks passwords and never carries the raw value."""
        alerts = [_Alert("SpyCloud", [_event(spycloud_password_plaintext="Sup3r$ecret")])]
        siemplify, _ = _make_siemplify(alerts)

        _run(siemplify)

        import json

        serialized = json.dumps(_json(siemplify))
        assert "Sup3r$ecret" not in serialized
        assert "length 11" in serialized

    def test_ignores_non_spycloud_events(self) -> None:
        other = _Event(additional_properties={"device_vendor": "SomeEDR", "foo": "bar"})
        siemplify, end_calls = _make_siemplify([_Alert("EDR Alert", [other])])

        _run(siemplify)

        assert end_calls[0]["result_value"] == 0
        assert _json(siemplify)["total_passwords"] == 0

    def test_groups_remaining_by_email(self) -> None:
        alerts = [
            _Alert(
                "SpyCloud",
                [
                    _event(spycloud_password_plaintext="Sup3r$ecret"),
                    _event(
                        spycloud_email="other@example.com",
                        spycloud_password_plaintext="short",
                    ),
                ],
            )
        ]
        siemplify, _ = _make_siemplify(alerts)

        _run(siemplify)

        payload = _json(siemplify)
        assert payload["emails_with_remaining_passwords"] == ["victim@example.com"]
