"""Tests for the SpyCloud Enterprise Check Password Rotation action.

The action compares the identity provider's last password change time against the
publish date of the case's SpyCloud exposures so the response playbooks can skip a
reset the user already performed. It makes no SpyCloud API call, so these tests
inject a fake case object rather than mocking the vendor SDK.

The decisive behavior is the default direction: anything the action cannot prove
stale must still come back as "reset required".
"""

from __future__ import annotations

import dataclasses
from typing import Any
from unittest.mock import MagicMock, patch

from spy_cloud_enterprise.actions import CheckPasswordRotation


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
        "spycloud_has_plaintext_password": "true",
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
    with patch.object(CheckPasswordRotation, "SiemplifyAction", return_value=siemplify):
        CheckPasswordRotation.main()


def _json(siemplify: MagicMock) -> dict[str, Any]:
    return siemplify.result.add_result_json.call_args.args[0]


class TestCheckPasswordRotation:
    def test_reset_skipped_when_password_changed_after_exposure(self) -> None:
        """The core case: the user already rotated, so the leak is dead."""
        alerts = [_Alert("SpyCloud", [_event(spycloud_publish_date="2026-06-14")])]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Last Password Reset Time": "2026-07-01T09:15:00.000Z"}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 0
        payload = _json(siemplify)
        assert payload["password_already_rotated"] is True
        assert payload["reset_required"] is False
        assert "No reset required" in end_calls[0]["message"]

    def test_reset_required_when_exposure_newer_than_reset(self) -> None:
        alerts = [_Alert("SpyCloud", [_event(spycloud_publish_date="2026-07-20")])]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Last Password Reset Time": "2026-07-01T09:15:00.000Z"}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1
        assert _json(siemplify)["password_already_rotated"] is False

    def test_exposure_published_same_instant_still_requires_reset(self) -> None:
        """Equal timestamps are ambiguous, so remediate rather than assume safety."""
        stamp = "2026-07-01T09:15:00Z"
        alerts = [_Alert("SpyCloud", [_event(spycloud_publish_date=stamp)])]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Last Password Reset Time": stamp}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1

    def test_missing_reset_time_requires_reset(self) -> None:
        """A get-user step that returned nothing must not cancel the reset."""
        alerts = [_Alert("SpyCloud", [_event(spycloud_publish_date="2026-06-14")])]
        siemplify, end_calls = _make_siemplify(alerts, params={})

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1
        assert "no usable last password reset time" in _json(siemplify)["reason"]

    def test_unparseable_reset_time_requires_reset(self) -> None:
        alerts = [_Alert("SpyCloud", [_event(spycloud_publish_date="2026-06-14")])]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Last Password Reset Time": "never"}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1

    def test_exposure_without_publish_date_requires_reset(self) -> None:
        alerts = [_Alert("SpyCloud", [_event()])]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Last Password Reset Time": "2026-07-01T09:15:00Z"}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1
        payload = _json(siemplify)
        assert payload["exposures_without_publish_date"] == 1
        assert "no SpyCloud exposure on this case carries a publish date" in payload["reason"]

    def test_latest_exposure_wins_across_events(self) -> None:
        """An old exposure must not mask a newer one on the same case."""
        alerts = [
            _Alert(
                "SpyCloud",
                [
                    _event(spycloud_publish_date="2026-01-01"),
                    _event(spycloud_publish_date="2026-07-20"),
                ],
            )
        ]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Last Password Reset Time": "2026-07-01T09:15:00Z"}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1
        assert _json(siemplify)["latest_exposure_publish_date"].startswith("2026-07-20")

    def test_falls_back_to_record_addition_date(self) -> None:
        """Cases ingested before the publish date was flattened still compare."""
        alerts = [
            _Alert("SpyCloud", [_event(spycloud_record_addition_date="2026-06-14")])
        ]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Last Password Reset Time": "2026-07-01T09:15:00Z"}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 0

    def test_email_filter_ignores_other_identities(self) -> None:
        """A newer exposure for a different user must not block this user's skip."""
        alerts = [
            _Alert(
                "SpyCloud",
                [
                    _event(spycloud_publish_date="2026-06-14"),
                    _event(
                        spycloud_email="other@example.com",
                        spycloud_publish_date="2026-07-20",
                    ),
                ],
            )
        ]
        siemplify, end_calls = _make_siemplify(
            alerts,
            params={
                "Last Password Reset Time": "2026-07-01T09:15:00Z",
                "Email": "Victim@Example.com",
            },
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 0
        assert _json(siemplify)["exposures_considered"] == 1

    def test_password_exposures_only_skips_cookie_records(self) -> None:
        """A newer cookie-only exposure is not something a reset remediates."""
        alerts = [
            _Alert(
                "SpyCloud",
                [
                    _event(spycloud_publish_date="2026-06-14"),
                    _event(
                        spycloud_has_plaintext_password="false",
                        spycloud_has_password="false",
                        spycloud_publish_date="2026-07-20",
                    ),
                ],
            )
        ]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Last Password Reset Time": "2026-07-01T09:15:00Z"}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 0
        assert _json(siemplify)["exposures_considered"] == 1

    def test_password_exposures_only_disabled_considers_every_record(self) -> None:
        alerts = [
            _Alert(
                "SpyCloud",
                [
                    _event(spycloud_publish_date="2026-06-14"),
                    _event(
                        spycloud_has_plaintext_password="false",
                        spycloud_has_password="false",
                        spycloud_publish_date="2026-07-20",
                    ),
                ],
            )
        ]
        siemplify, end_calls = _make_siemplify(
            alerts,
            params={
                "Last Password Reset Time": "2026-07-01T09:15:00Z",
                "Password Exposures Only": False,
            },
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1
        assert _json(siemplify)["exposures_considered"] == 2

    def test_non_spycloud_events_are_ignored(self) -> None:
        other = _Event(additional_properties={"device_vendor": "Acme", "publish": "x"})
        alerts = [_Alert("Other", [other])]
        siemplify, end_calls = _make_siemplify(
            alerts, params={"Last Password Reset Time": "2026-07-01T09:15:00Z"}
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1
        assert _json(siemplify)["exposures_considered"] == 0

    def test_never_surfaces_password_values(self) -> None:
        """The JSON result carries timestamps and counts, never a secret."""
        alerts = [
            _Alert(
                "SpyCloud",
                [
                    _event(
                        spycloud_password_plaintext="Sup3r$ecret",
                        spycloud_publish_date="2026-06-14",
                    )
                ],
            )
        ]
        siemplify, _ = _make_siemplify(
            alerts, params={"Last Password Reset Time": "2026-07-01T09:15:00Z"}
        )

        _run(siemplify)

        import json

        assert "Sup3r$ecret" not in json.dumps(_json(siemplify))

    def test_action_failure_still_requests_a_reset(self) -> None:
        """An unexpected error must fail toward remediation, not silently skip."""
        siemplify, end_calls = _make_siemplify([])
        siemplify.case.alerts = MagicMock(
            __bool__=lambda _self: True,
            __iter__=MagicMock(side_effect=RuntimeError("boom")),
        )

        _run(siemplify)

        assert end_calls[0]["result_value"] == 1
        assert "Error executing action" in end_calls[0]["message"]
