# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest.mock import patch, MagicMock

import pytest

from microsoft365_defender.jobs.SyncAlerts import SyncAlerts

_GET_M365_ALERT_ID_PATH = (
    "microsoft365_defender.jobs.SyncAlerts"
    ".get_m365_alert_id_from_soar_alert"
)


# pylint: disable=redefined-outer-name
@pytest.fixture
def sync_alerts():
    """Prepare a SyncAlerts instance for testing with mocked base class."""
    with patch(
        "microsoft365_defender.jobs.SyncAlerts.BaseSyncJob.__init__",
        return_value=None,
    ):
        instance = SyncAlerts.__new__(SyncAlerts)
        instance._logger = MagicMock()
        instance.manager = MagicMock()
        instance._soar_job = MagicMock()
        instance.sync_product_status_to_case = MagicMock()
        instance._remove_synced_entries = MagicMock()
        yield instance


# ---------------------------------------------------------------------------
# _close_alerts_due_to_redirection
# ---------------------------------------------------------------------------


def test_close_alerts_due_to_redirection_closes_all_alerts(sync_alerts):
    """Test that _close_alerts_due_to_redirection calls sync_product_status_to_case
    and _remove_synced_entries for every alert in the list."""
    alert_1 = MagicMock()
    alert_1.identifier = "alert-1"
    alert_2 = MagicMock()
    alert_2.identifier = "alert-2"

    job_case = MagicMock()
    job_case.case_detail.id_ = "case-100"

    with patch(
        _GET_M365_ALERT_ID_PATH,
        side_effect=["m365-1", "m365-2"],
    ) as mock_get_id:
        sync_alerts._close_alerts_due_to_redirection(
            job_case=job_case,
            parent_incident_id="parent-inc-1",
            alerts=[alert_1, alert_2],
        )

    assert sync_alerts.sync_product_status_to_case.call_count == 2
    assert sync_alerts._remove_synced_entries.call_count == 2
    assert mock_get_id.call_count == 2

    first_call_args = sync_alerts.sync_product_status_to_case.call_args_list[0]
    comment_arg = first_call_args.args[-1]
    assert "parent-inc-1" in comment_arg


def test_close_alerts_due_to_redirection_empty_alerts(sync_alerts):
    """Test that _close_alerts_due_to_redirection does nothing when alerts list
    is empty."""
    job_case = MagicMock()
    job_case.case_detail.id_ = "case-200"

    sync_alerts._close_alerts_due_to_redirection(
        job_case=job_case,
        parent_incident_id="parent-inc-2",
        alerts=[],
    )

    sync_alerts.sync_product_status_to_case.assert_not_called()
    sync_alerts._remove_synced_entries.assert_not_called()


def test_close_alerts_due_to_redirection_logs_info(sync_alerts):
    """Test that _close_alerts_due_to_redirection logs an info message containing
    the parent incident id and alert identifiers."""
    alert = MagicMock()
    alert.identifier = "alert-99"

    job_case = MagicMock()
    job_case.case_detail.id_ = "case-300"

    with patch(
        _GET_M365_ALERT_ID_PATH,
        return_value="m365-99",
    ):
        sync_alerts._close_alerts_due_to_redirection(
            job_case=job_case,
            parent_incident_id="parent-inc-99",
            alerts=[alert],
        )

    sync_alerts.logger.info.assert_called_once()
    log_message = sync_alerts.logger.info.call_args.args[0]
    assert "parent-inc-99" in log_message
    assert "alert-99" in log_message


# ---------------------------------------------------------------------------
# _sync_case_name
# ---------------------------------------------------------------------------


def test_sync_case_name_renames_when_names_differ(sync_alerts):
    """Test that _sync_case_name calls rename_case when the case name differs from
    the parent incident name."""
    job_case = MagicMock()
    job_case.case_detail.id_ = "case-1"
    job_case.case_detail.name = "Old Case Name"

    parent_incident = MagicMock()
    parent_incident.incident_name = "New Incident Name"

    with patch(
        "microsoft365_defender.jobs.SyncAlerts.rename_case"
    ) as mock_rename:
        sync_alerts._sync_case_name(job_case, parent_incident)

        mock_rename.assert_called_once_with(
            sync_alerts.soar_job,
            "case-1",
            "New Incident Name",
        )


def test_sync_case_name_does_not_rename_when_names_match(sync_alerts):
    """Test that _sync_case_name does not call rename_case when names are the same."""
    job_case = MagicMock()
    job_case.case_detail.id_ = "case-2"
    job_case.case_detail.name = "Same Name"

    parent_incident = MagicMock()
    parent_incident.incident_name = "Same Name"

    with patch(
        "microsoft365_defender.jobs.SyncAlerts.rename_case"
    ) as mock_rename:
        sync_alerts._sync_case_name(job_case, parent_incident)

        mock_rename.assert_not_called()


def test_sync_case_name_does_not_rename_when_incident_name_empty(sync_alerts):
    """Test that _sync_case_name returns early when parent incident has no name."""
    job_case = MagicMock()
    job_case.case_detail.id_ = "case-3"

    parent_incident = MagicMock()
    parent_incident.incident_name = ""

    with patch(
        "microsoft365_defender.jobs.SyncAlerts.rename_case"
    ) as mock_rename:
        sync_alerts._sync_case_name(job_case, parent_incident)

        mock_rename.assert_not_called()


def test_sync_case_name_logs_when_renaming(sync_alerts):
    """Test that _sync_case_name logs an info message when renaming."""
    job_case = MagicMock()
    job_case.case_detail.id_ = "case-4"
    job_case.case_detail.name = "Old Name"

    parent_incident = MagicMock()
    parent_incident.incident_name = "New Name"

    with patch(
        "microsoft365_defender.jobs.SyncAlerts.rename_case"
    ):
        sync_alerts._sync_case_name(job_case, parent_incident)

        sync_alerts.logger.info.assert_called_once()
        log_message = sync_alerts.logger.info.call_args.args[0]
        assert "case-4" in log_message
        assert "Old Name" in log_message
        assert "New Name" in log_message


def test_parse_iso_datetime_handles_none_and_invalid():
    """Test that parse_iso_datetime returns None for None, non-string, or empty input."""
    from microsoft365_defender.core.UtilsManager import parse_iso_datetime

    assert parse_iso_datetime(None) is None
    assert parse_iso_datetime("") is None
    assert parse_iso_datetime(12345) is None
    parsed = parse_iso_datetime("2026-08-10T10:00:00Z")
    assert parsed is not None
    assert parsed.year == 2026


def test_filter_alert_ids_handles_none_timestamps(sync_alerts):
    """Test that _filter_alert_ids ignores alerts with None or missing timestamps."""
    from microsoft365_defender.core.UtilsManager import parse_iso_datetime

    sync_alerts.last_run_time = 1000000000000  # set last_run_time

    alert_no_ts = MagicMock()
    alert_no_ts.raw_data = {"lastUpdateDateTime": None, "createdDateTime": None}
    alert_no_ts.alert_id = "alert-1"

    alert_valid = MagicMock()
    alert_valid.raw_data = {"lastUpdateDateTime": "2099-01-01T00:00:00Z"}
    alert_valid.alert_id = "alert-2"

    filtered = sync_alerts._filter_alert_ids([alert_no_ts, alert_valid])
    assert filtered == ["alert-2"]


def test_filter_alert_ids_returns_empty_when_no_valid_alerts(sync_alerts):
    """Test that _filter_alert_ids returns empty list if no valid/newer alerts found."""
    sync_alerts.last_run_time = 1000000000000

    alert_none = MagicMock()
    alert_none.raw_data = {}
    alert_none.alert_id = "alert-1"

    filtered = sync_alerts._filter_alert_ids([alert_none])
    assert filtered == []
