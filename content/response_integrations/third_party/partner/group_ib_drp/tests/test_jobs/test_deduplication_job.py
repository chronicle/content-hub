"""Unit tests for the ``DRP Deduplication Job``.

The dedup job is the highest-stakes piece of new automation in this PR
— it issues mutating REST calls (``cases:merge``) and ``close_case``
operations that are extremely hard to reverse. The tests below pin down:

* The two operating modes (``merge`` and ``close``) keep the right side
  effects and are correctly fenced behind the ``Dry Run`` flag.
* Helper utilities (URL resolution, tag normalisation,
  ``rule_generator`` re-verification) handle each documented scenario.
* The end-to-end pipeline correctly groups duplicates by violation UID
  and never reconciles a case against itself.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ..common import JOBS_PATH, load_script


@pytest.fixture
def job_module():
    return load_script(JOBS_PATH, "DRP Deduplication Job.py", "DRPDeduplicationJob")


def _job_params(**overrides) -> dict:
    """Defaults that match the job's UI parameter shape."""
    base = {
        "Case Type": "Violations",
        "Max Cases To Process": 100,
        "Lookback Days": 30,
        "Dry Run": True,
        "Close Root Cause": "Duplicate",
        "Close Reason": "Maintenance",
        "Carry Over To Primary": False,
        "Merge Mode": "merge",
        "Chronicle Instance Path": "",
    }
    base.update(overrides)
    return base


def _make_case(
    *,
    status: int = 1,
    creation_time: int = 1_700_000_000_000,
    cyber_alerts: list | None = None,
    tags: list | None = None,
    environment: str = "Default Environment",
) -> dict:
    return {
        "status": status,
        "creation_time": creation_time,
        "cyber_alerts": cyber_alerts or [],
        "tags": list(tags or []),
        "environment": environment,
    }


def _make_alert(
    *,
    rule_generator: str = "Violations: example.com",
    ticket_id: str = "uid-1",
    identifier: str = "alert-1",
    entities: list | None = None,
    tags: list | None = None,
    additional_properties: dict | None = None,
) -> dict:
    return {
        "rule_generator": rule_generator,
        "ticket_id": ticket_id,
        "identifier": identifier,
        "entities": list(entities or []),
        "tags": list(tags or []),
        "additional_properties": dict(additional_properties or {}),
    }


# ─── Pure helpers ────────────────────────────────────────────────────────


class TestTagNameNormalization:
    """``_tag_name`` accepts strings and dicts; anything else returns ''."""

    def test_string_tag_is_stripped(self, job_module):
        assert job_module._tag_name("  phishing  ") == "phishing"

    def test_dict_tag_uses_name_field(self, job_module):
        assert job_module._tag_name({"name": "high-risk"}) == "high-risk"

    def test_dict_tag_uses_tag_field_when_name_absent(self, job_module):
        assert job_module._tag_name({"tag": "fallback"}) == "fallback"

    def test_unknown_tag_shape_returns_empty_string(self, job_module):
        assert job_module._tag_name(None) == ""
        assert job_module._tag_name(123) == ""


class TestStripTrailingApi:
    """``_strip_trailing_api`` strips trailing ``/api`` and trailing slashes."""

    def test_strips_api_suffix(self, job_module):
        assert (
            job_module._strip_trailing_api("https://soar.example.com/api")
            == "https://soar.example.com"
        )

    def test_strips_trailing_slash_first(self, job_module):
        assert (
            job_module._strip_trailing_api("https://soar.example.com/api/")
            == "https://soar.example.com"
        )

    def test_no_op_when_no_api_suffix(self, job_module):
        assert (
            job_module._strip_trailing_api("https://soar.example.com")
            == "https://soar.example.com"
        )

    def test_handles_none_and_empty(self, job_module):
        assert job_module._strip_trailing_api(None) == ""
        assert job_module._strip_trailing_api("") == ""


# ─── URL resolution ─────────────────────────────────────────────────────


class TestResolveMergeUrl:
    """``_resolve_merge_url`` walks two strategies in order: auto-detect,
    then operator-supplied override. Each branch must produce a URL that
    can actually receive a v1beta cases.merge request."""

    def test_auto_detects_via_sdk_config(self, job_module, job_siemplify_factory):
        """Healthy tenants — ``sdk_config.one_platform_api_root_uri_format``
        renders a Chronicle resource path and we use it."""
        siemplify = job_siemplify_factory()
        siemplify.sdk_config = SimpleNamespace(
            one_platform_api_root_uri_format=(
                "https://chronicle.example.com/{}/projects/p/locations/l/instances/i"
            )
        )
        url, source = job_module._resolve_merge_url(siemplify, instance_path_override="")
        assert url == (
            "https://chronicle.example.com/v1beta/projects/p/locations/l/instances/i/cases:merge"
        )
        assert "auto-detected" in source

    def test_falls_back_to_override_when_sdk_config_uses_placeholders(
        self, job_module, job_siemplify_factory
    ):
        """When sdk_config still has the placeholder literals, we must
        fall through to the operator-supplied override."""

        siemplify = job_siemplify_factory()
        siemplify.sdk_config = SimpleNamespace(
            one_platform_api_root_uri_format=(
                "https://chronicle.example.com/{}/projects/project/locations/location/instances/instance"
            )
        )
        siemplify.API_ROOT = "https://soar.example.com/api"
        url, source = job_module._resolve_merge_url(
            siemplify,
            instance_path_override="projects/p/locations/l/instances/i",
        )
        assert url == (
            "https://soar.example.com/v1beta/projects/p/locations/l/instances/i/cases:merge"
        )
        assert "override" in source

    def test_returns_none_when_neither_strategy_works(
        self, job_module, job_siemplify_factory
    ):
        siemplify = job_siemplify_factory()
        siemplify.sdk_config = SimpleNamespace(one_platform_api_root_uri_format=None)
        url, reason = job_module._resolve_merge_url(siemplify, instance_path_override="")
        assert url is None
        assert "auto-detection failed" in reason

    def test_returns_none_when_override_lacks_path_segment(
        self, job_module, job_siemplify_factory
    ):
        siemplify = job_siemplify_factory()
        siemplify.sdk_config = SimpleNamespace(one_platform_api_root_uri_format=None)
        url, _reason = job_module._resolve_merge_url(
            siemplify, instance_path_override="bogus/value"
        )
        assert url is None


# ─── _merge_cases_v1beta ────────────────────────────────────────────────


class TestMergeCases:
    """``_merge_cases_v1beta`` is the only place this job hits a destructive
    REST endpoint; cover every branch that can short-circuit the POST."""

    def test_dry_run_does_not_post(self, job_module, job_siemplify_factory):
        siemplify = job_siemplify_factory()
        ok = job_module._merge_cases_v1beta(
            siemplify=siemplify,
            merge_url="https://chronicle.example.com/v1beta/.../cases:merge",
            primary_case_id="100",
            duplicate_case_id="101",
            duplicate_rule_generator="Violations: example.com",
            uid="uid-x",
            case_type="Violations",
            dry_run=True,
        )
        assert ok is True
        siemplify.session.post.assert_not_called()

    def test_skips_when_rule_generator_no_longer_matches(
        self, job_module, job_siemplify_factory
    ):
        siemplify = job_siemplify_factory()
        ok = job_module._merge_cases_v1beta(
            siemplify=siemplify,
            merge_url="https://chronicle.example.com/v1beta/.../cases:merge",
            primary_case_id="100",
            duplicate_case_id="101",
            duplicate_rule_generator="OtherType: example.com",
            uid="uid-x",
            case_type="Violations",
            dry_run=False,
        )
        assert ok is False
        siemplify.session.post.assert_not_called()

    def test_skips_when_case_ids_are_not_integers(
        self, job_module, job_siemplify_factory
    ):
        """``cases.merge`` rejects non-integer IDs — we must short-circuit
        before the POST so the error surfaces as a single warn, not 50."""
        siemplify = job_siemplify_factory()
        ok = job_module._merge_cases_v1beta(
            siemplify=siemplify,
            merge_url="https://chronicle.example.com/v1beta/.../cases:merge",
            primary_case_id="not-an-int",
            duplicate_case_id="also-not-an-int",
            duplicate_rule_generator="Violations: example.com",
            uid="uid-x",
            case_type="Violations",
            dry_run=False,
        )
        assert ok is False
        siemplify.session.post.assert_not_called()

    def test_posts_documented_payload_on_success(
        self, job_module, job_siemplify_factory
    ):
        """The ``casesIds`` list MUST include both the duplicate AND the
        primary; passing only the duplicate causes server-side rejection."""
        siemplify = job_siemplify_factory()
        response = MagicMock()
        response.json.return_value = {"isRequestValid": True, "errors": [], "newCaseId": 200}
        response.raise_for_status.return_value = None
        siemplify.session.post.return_value = response

        ok = job_module._merge_cases_v1beta(
            siemplify=siemplify,
            merge_url="https://chronicle.example.com/v1beta/.../cases:merge",
            primary_case_id="100",
            duplicate_case_id="101",
            duplicate_rule_generator="Violations: example.com",
            uid="uid-x",
            case_type="Violations",
            dry_run=False,
        )
        assert ok is True
        siemplify.session.post.assert_called_once()
        url_arg, = siemplify.session.post.call_args.args
        body = siemplify.session.post.call_args.kwargs["json"]
        assert url_arg.endswith("cases:merge")
        assert body == {"casesIds": [101, 100], "caseToMergeWith": 100}

    def test_returns_false_when_response_reports_errors(
        self, job_module, job_siemplify_factory
    ):
        siemplify = job_siemplify_factory()
        response = MagicMock()
        response.json.return_value = {
            "isRequestValid": False,
            "errors": ["case already merged"],
        }
        response.raise_for_status.return_value = None
        siemplify.session.post.return_value = response

        ok = job_module._merge_cases_v1beta(
            siemplify=siemplify,
            merge_url="https://chronicle.example.com/v1beta/.../cases:merge",
            primary_case_id="100",
            duplicate_case_id="101",
            duplicate_rule_generator="Violations: example.com",
            uid="uid-x",
            case_type="Violations",
            dry_run=False,
        )
        assert ok is False


# ─── _close_duplicate_with_reference ────────────────────────────────────


class TestCloseDuplicate:
    """The close-mode path. Each branch is exercised independently."""

    def test_dry_run_does_not_call_close_case(self, job_module, job_siemplify_factory):
        siemplify = job_siemplify_factory()
        ok = job_module._close_duplicate_with_reference(
            siemplify=siemplify,
            primary_case_id="100",
            primary_alert_id="alert-100",
            duplicate_case_id="101",
            duplicate_alert_id="alert-101",
            duplicate_rule_generator="Violations: example.com",
            uid="uid-x",
            case_type="Violations",
            close_root_cause="Duplicate",
            close_reason="Maintenance",
            dry_run=True,
        )
        assert ok is True
        siemplify.close_case.assert_not_called()
        siemplify.add_comment.assert_not_called()

    def test_skips_when_rule_generator_no_longer_matches(
        self, job_module, job_siemplify_factory
    ):
        siemplify = job_siemplify_factory()
        ok = job_module._close_duplicate_with_reference(
            siemplify=siemplify,
            primary_case_id="100",
            primary_alert_id="alert-100",
            duplicate_case_id="101",
            duplicate_alert_id="alert-101",
            duplicate_rule_generator="OtherType: example.com",
            uid="uid-x",
            case_type="Violations",
            close_root_cause="Duplicate",
            close_reason="Maintenance",
            dry_run=False,
        )
        assert ok is False
        siemplify.close_case.assert_not_called()

    def test_closes_duplicate_and_back_references_primary(
        self, job_module, job_siemplify_factory
    ):
        """``close_case`` runs against the duplicate, then a comment is
        added to the *primary* pointing back at the duplicate."""
        siemplify = job_siemplify_factory()
        ok = job_module._close_duplicate_with_reference(
            siemplify=siemplify,
            primary_case_id="100",
            primary_alert_id="alert-100",
            duplicate_case_id="101",
            duplicate_alert_id="alert-101",
            duplicate_rule_generator="Violations",
            uid="uid-x",
            case_type="Violations",
            close_root_cause="Duplicate",
            close_reason="Maintenance",
            dry_run=False,
        )
        assert ok is True
        siemplify.close_case.assert_called_once()
        kw = siemplify.close_case.call_args.kwargs
        assert kw["case_id"] == "101"
        assert kw["alert_identifier"] == "alert-101"
        assert "Duplicate of case 100" in kw["comment"]

        siemplify.add_comment.assert_called_once()
        comment_text, primary_case_id, primary_alert_id = siemplify.add_comment.call_args.args
        assert "Closed duplicate case 101" in comment_text
        assert primary_case_id == "100"
        assert primary_alert_id == "alert-100"


# ─── _carry_over_to_primary ─────────────────────────────────────────────


class TestCarryOverToPrimary:
    """Carry-over moves analyst comments/tags/entities from the duplicate
    onto the primary. The behaviour we lock down is best-effort:
    sub-step failures are logged but never raise."""

    def test_carries_user_comments_skips_dedup_back_references(
        self, job_module, job_siemplify_factory
    ):
        siemplify = job_siemplify_factory()
        siemplify.get_case_comments.return_value = [
            {"comment": "investigated; phishing confirmed"},
            {"comment": "[DRP Dedup] Closed duplicate case ..."},
            {"comment": ""},
        ]
        primary = {
            "case_id": "100",
            "alert_identifier": "alert-100",
            "case_tags": [],
            "alert_tags": [],
            "entities": [],
            "environment": "env",
        }
        duplicate = {
            "case_id": "101",
            "alert_identifier": "alert-101",
            "case_tags": [],
            "alert_tags": [],
            "entities": [],
            "environment": "env",
        }

        job_module._carry_over_to_primary(
            siemplify=siemplify, primary=primary, duplicate=duplicate, dry_run=False
        )

        assert siemplify.add_comment.call_count == 1
        wrapped = siemplify.add_comment.call_args.args[0]
        assert "investigated; phishing confirmed" in wrapped
        assert "[from merged case #101]" in wrapped

    def test_skips_tags_already_present_on_primary(
        self, job_module, job_siemplify_factory
    ):
        siemplify = job_siemplify_factory()
        siemplify.get_case_comments.return_value = []
        primary = {
            "case_id": "100",
            "alert_identifier": "alert-100",
            "case_tags": ["already-here"],
            "alert_tags": [],
            "entities": [],
            "environment": "env",
        }
        duplicate = {
            "case_id": "101",
            "alert_identifier": "alert-101",
            "case_tags": ["already-here"],
            "alert_tags": ["new-tag"],
            "entities": [],
            "environment": "env",
        }

        job_module._carry_over_to_primary(
            siemplify=siemplify, primary=primary, duplicate=duplicate, dry_run=False
        )

        assert siemplify.add_tag.call_count == 1
        added_tag = siemplify.add_tag.call_args.args[0]
        assert added_tag == "new-tag"

    def test_skips_entities_already_on_primary(
        self, job_module, job_siemplify_factory
    ):
        siemplify = job_siemplify_factory()
        siemplify.get_case_comments.return_value = []
        primary = {
            "case_id": "100",
            "alert_identifier": "alert-100",
            "case_tags": [],
            "alert_tags": [],
            "entities": [{"identifier": "https://bad.example.com/a"}],
            "environment": "env",
        }
        duplicate = {
            "case_id": "101",
            "alert_identifier": "alert-101",
            "case_tags": [],
            "alert_tags": [],
            "entities": [
                {"identifier": "https://bad.example.com/a"},  # already present
                {
                    "identifier": "https://bad.example.com/b",
                    "entity_type": "DestinationURL",
                    "additional_properties": {"violation_uid": "uid-b"},
                },
            ],
            "environment": "env",
        }

        job_module._carry_over_to_primary(
            siemplify=siemplify, primary=primary, duplicate=duplicate, dry_run=False
        )

        assert siemplify.add_entity_to_case.call_count == 1
        kw = siemplify.add_entity_to_case.call_args.kwargs
        assert kw["entity_identifier"] == "https://bad.example.com/b"
        assert kw["case_id"] == "100"
        assert kw["entity_type"] == "DestinationURL"

    def test_dry_run_does_no_writes(self, job_module, job_siemplify_factory):
        siemplify = job_siemplify_factory()
        siemplify.get_case_comments.return_value = [{"comment": "user note"}]
        primary = {
            "case_id": "100",
            "alert_identifier": "alert-100",
            "case_tags": [],
            "alert_tags": [],
            "entities": [],
            "environment": "env",
        }
        duplicate = {
            "case_id": "101",
            "alert_identifier": "alert-101",
            "case_tags": ["t1"],
            "alert_tags": [],
            "entities": [{"identifier": "https://bad.example.com/x"}],
            "environment": "env",
        }

        job_module._carry_over_to_primary(
            siemplify=siemplify, primary=primary, duplicate=duplicate, dry_run=True
        )

        siemplify.add_comment.assert_not_called()
        siemplify.add_tag.assert_not_called()
        siemplify.add_entity_to_case.assert_not_called()


# ─── End-to-end main() ──────────────────────────────────────────────────


class TestJobMain:
    """End-to-end orchestration tests. We don't try to cover every
    permutation here; we cover a representative subset that proves the
    pipeline keeps a primary alive and reconciles its duplicate."""

    def test_close_mode_dry_run_records_plan_without_mutation(
        self, job_module, job_siemplify_factory
    ):
        """Two cases sharing the same UID. Close-mode + dry-run → the
        duplicate is *not* closed, but the plan is produced."""

        params = _job_params(**{"Merge Mode": "close", "Dry Run": True})
        cases_by_id = {
            "100": _make_case(
                creation_time=1_000,
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Violations: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-100",
                    )
                ],
            ),
            "101": _make_case(
                creation_time=2_000,
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Violations: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-101",
                    )
                ],
            ),
        }
        siemplify = job_siemplify_factory(
            parameters=params,
            case_ids=["100", "101"],
            cases_by_id=cases_by_id,
        )

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        siemplify.close_case.assert_not_called()
        siemplify.add_comment.assert_not_called()
        siemplify.end_script.assert_called_once()

    def test_close_mode_real_run_closes_duplicate_only(
        self, job_module, job_siemplify_factory
    ):
        """Two cases sharing the same UID. Close-mode + real run → exactly
        one ``close_case`` call against the *newer* duplicate, not the
        primary."""

        params = _job_params(**{"Merge Mode": "close", "Dry Run": False})
        cases_by_id = {
            "100": _make_case(
                creation_time=1_000,
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Violations: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-100",
                    )
                ],
            ),
            "101": _make_case(
                creation_time=2_000,
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Violations: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-101",
                    )
                ],
            ),
        }
        siemplify = job_siemplify_factory(
            parameters=params,
            case_ids=["100", "101"],
            cases_by_id=cases_by_id,
        )

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        siemplify.close_case.assert_called_once()
        assert siemplify.close_case.call_args.kwargs["case_id"] == "101"

    def test_skips_uids_with_only_one_case(self, job_module, job_siemplify_factory):
        """A unique UID is not a duplicate; nothing should be closed/merged."""

        params = _job_params(**{"Merge Mode": "close", "Dry Run": False})
        cases_by_id = {
            "100": _make_case(
                cyber_alerts=[
                    _make_alert(ticket_id="uid-unique", identifier="alert-100")
                ]
            )
        }
        siemplify = job_siemplify_factory(
            parameters=params, case_ids=["100"], cases_by_id=cases_by_id
        )

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        siemplify.close_case.assert_not_called()

    def test_caps_at_max_cases_to_process(self, job_module, job_siemplify_factory):
        """``Max Cases To Process`` caps the *case ID list*, not the alert
        list. We expect ``_get_case_by_id`` to be called only ``max_cases``
        times even if the filter returned more IDs."""

        params = _job_params(
            **{"Max Cases To Process": 1, "Merge Mode": "close", "Dry Run": True}
        )
        cases_by_id = {
            "100": _make_case(
                cyber_alerts=[
                    _make_alert(ticket_id="uid-1", identifier="alert-100")
                ]
            ),
            "101": _make_case(
                cyber_alerts=[
                    _make_alert(ticket_id="uid-1", identifier="alert-101")
                ]
            ),
            "102": _make_case(
                cyber_alerts=[
                    _make_alert(ticket_id="uid-1", identifier="alert-102")
                ]
            ),
        }
        siemplify = job_siemplify_factory(
            parameters=params,
            case_ids=["100", "101", "102"],
            cases_by_id=cases_by_id,
        )

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        assert siemplify._get_case_by_id.call_count == 1

    def test_skips_alerts_whose_rule_generator_does_not_match_case_type(
        self, job_module, job_siemplify_factory
    ):
        """An alert from a different connector should be ignored entirely
        even if its case is OPEN within the lookback window."""

        params = _job_params(**{"Merge Mode": "close", "Dry Run": False})
        cases_by_id = {
            "100": _make_case(
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Typosquatting: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-100",
                    )
                ]
            ),
            "101": _make_case(
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Typosquatting: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-101",
                    )
                ]
            ),
        }
        siemplify = job_siemplify_factory(
            parameters=params,
            case_ids=["100", "101"],
            cases_by_id=cases_by_id,
        )

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        siemplify.close_case.assert_not_called()

    def test_aborts_when_merge_mode_url_cannot_be_resolved(
        self, job_module, job_siemplify_factory
    ):
        """In merge mode, if the URL can't be resolved we end_script and
        emit nothing — never silently fall back to close mode."""
        params = _job_params(**{"Merge Mode": "merge", "Chronicle Instance Path": ""})
        siemplify = job_siemplify_factory(parameters=params)
        siemplify.sdk_config = SimpleNamespace(one_platform_api_root_uri_format=None)

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        siemplify.end_script.assert_called_once()
        siemplify.get_cases_ids_by_filter.assert_not_called()
        siemplify.session.post.assert_not_called()

    def test_unknown_merge_mode_falls_back_to_merge_mode(
        self, job_module, job_siemplify_factory
    ):
        """An unrecognised merge_mode value should fall back to ``merge``,
        which means the URL must still resolve — wire that up."""
        params = _job_params(**{"Merge Mode": "unknown-mode"})
        siemplify = job_siemplify_factory(parameters=params)
        siemplify.sdk_config = SimpleNamespace(
            one_platform_api_root_uri_format=(
                "https://chronicle.example.com/{}/projects/p/locations/l/instances/i"
            )
        )
        siemplify.LOGGER.error = MagicMock(name="error")

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        siemplify.LOGGER.error.assert_called()
        first_error = siemplify.LOGGER.error.call_args_list[0].args[0]
        assert "Unrecognised Merge Mode" in first_error

    def test_carry_over_redundancy_warning_in_merge_mode(
        self, job_module, job_siemplify_factory
    ):
        """Merge mode + carry_over=True logs an info that carry-over is
        redundant. We don't enforce silencing the flag because the
        cascading downstream behaviour is already covered above; we just
        verify the operator sees the warning."""

        params = _job_params(
            **{"Merge Mode": "merge", "Carry Over To Primary": True, "Dry Run": True}
        )
        siemplify = job_siemplify_factory(parameters=params)
        siemplify.sdk_config = SimpleNamespace(
            one_platform_api_root_uri_format=(
                "https://chronicle.example.com/{}/projects/p/locations/l/instances/i"
            )
        )

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        all_info = " | ".join(c.args[0] for c in siemplify.LOGGER.info.call_args_list)
        assert "Carry Over To Primary is redundant" in all_info

    def test_skips_self_pair_when_primary_and_duplicate_are_same_case(
        self, job_module, job_siemplify_factory
    ):
        """A single OPEN case with two alerts that share the same UID can
        end up registering itself twice under that UID. The job's
        per-case dedup guard prevents that, so ``close_case`` must NOT
        be called for the case against itself."""

        params = _job_params(**{"Merge Mode": "close", "Dry Run": False})
        cases_by_id = {
            "100": _make_case(
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Violations: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-100",
                    ),
                    _make_alert(
                        rule_generator="Violations: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-100b",
                    ),
                ]
            ),
        }
        siemplify = job_siemplify_factory(
            parameters=params, case_ids=["100"], cases_by_id=cases_by_id
        )

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        siemplify.close_case.assert_not_called()

    def test_skips_cases_whose_status_is_not_open(
        self, job_module, job_siemplify_factory
    ):
        """A case the filter returned but that's no longer OPEN must be
        skipped (not closed again, not merged)."""
        params = _job_params(**{"Merge Mode": "close", "Dry Run": False})
        cases_by_id = {
            "100": _make_case(
                status=2,  # not OPEN
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Violations: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-100",
                    )
                ],
            ),
            "101": _make_case(
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Violations: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-101",
                    )
                ]
            ),
        }
        siemplify = job_siemplify_factory(
            parameters=params, case_ids=["100", "101"], cases_by_id=cases_by_id
        )

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        siemplify.close_case.assert_not_called()

    def test_handles_get_case_by_id_failures_gracefully(
        self, job_module, job_siemplify_factory
    ):
        """A failed ``_get_case_by_id`` for one case must not abort the
        whole run — the remaining cases must still be processed."""
        params = _job_params(**{"Merge Mode": "close", "Dry Run": False})

        def selective_fetch(cid):
            if cid == "100":
                raise Exception("HTTP 500")
            return _make_case(
                cyber_alerts=[
                    _make_alert(
                        rule_generator="Violations: example.com",
                        ticket_id="uid-shared",
                        identifier="alert-{}".format(cid),
                    )
                ]
            )

        siemplify = job_siemplify_factory(parameters=params, case_ids=["100", "101"])
        siemplify._get_case_by_id.side_effect = selective_fetch

        with patch.object(job_module, "SiemplifyJob", return_value=siemplify):
            job_module.main()

        siemplify.close_case.assert_not_called()
        siemplify.LOGGER.warning.assert_called()
