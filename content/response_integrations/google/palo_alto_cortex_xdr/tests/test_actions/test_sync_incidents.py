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

from __future__ import annotations
import pathlib

import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytz
from TIPCommon.data_models import CaseDetails
from TIPCommon.types import SingleJson

from palo_alto_cortex_xdr.jobs.SyncIncidents import SyncIncidents
from palo_alto_cortex_xdr.core.datamodels import IncidentInfo
from palo_alto_cortex_xdr.tests import common
from palo_alto_cortex_xdr.tests.common import (
    CASE_ID,
    CONNECTOR_INCIDENT_ID,
    MOCK_CASE_IDENTIFIER,
    get_mock_case_details,
    get_mock_incident,
    get_mock_incident_extra_data,
)
from palo_alto_cortex_xdr.tests.core.product import PaloAltoCortexXDR
from palo_alto_cortex_xdr.tests.core.session import (
    PaloAltoCortexXDRSOARSession,
)

from integration_testing.set_meta import set_metadata

DEFAULT_PARAMETERS: SingleJson = {
    "Max Hours Backwards": "24",
    "Environment Name": "Default",
    "Verify SSL": False,
    "Api Root": "https://test.com",
    "Api Key": "test_api_key",
    "Api Key ID": "00",
    "User Mapping JSON": "{}",
}


def mock_soar_job_for_run(soar_job: SyncIncidents) -> None:
    """
    Mock the Siemplify object and its methods for a job run.

    Args:
        soar_job: The Siemplify object to mock.
    """
    now: datetime.datetime = datetime.datetime.now(pytz.utc)
    last_run_time: datetime.datetime = now - datetime.timedelta(
        hours=int(DEFAULT_PARAMETERS["Max Hours Backwards"])
    )
    mock_case: CaseDetails = get_mock_case_details()

    soar_job.soar_job.fetch_timestamp = MagicMock(return_value=last_run_time)
    # pylint: disable=protected-access
    soar_job._get_case_ids_by_timestamp = MagicMock(
        return_value=[(CASE_ID, int(now.timestamp() * 1000))]
    )
    # pylint: disable=protected-access
    soar_job._save_timestamp_by_unique_id = MagicMock()
    soar_job.case_details = {CASE_ID: mock_case}
    soar_job.soar_job.get_context_property = MagicMock(return_value=None)
    soar_job.soar_job.get_case_closure_details = MagicMock(return_value=[])
    soar_job.soar_job.fetch_case_comments = MagicMock(return_value=[])
    soar_job.soar_job.save_timestamp = MagicMock()
    soar_job.soar_job.close_alert = MagicMock()
    soar_job.soar_job.add_comment = MagicMock()

    if mock_case.alerts:
        soar_job.soar_job.get_alerts_by_filter = MagicMock(
            return_value=mock_case.alerts
        )

        patcher: Any = patch.object(
            soar_job,
            "_read_state",  # pylint: disable=protected-access
            return_value={CASE_ID: [str(CONNECTOR_INCIDENT_ID)]},
        )

        patcher.start()


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_job_runs_successfully(
    soar_sdk_session: PaloAltoCortexXDRSOARSession,
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
) -> None:
    soar_job: SyncIncidents = SyncIncidents()
    mock_soar_job_for_run(soar_job)

    soar_job.soar_job.get_case_closure_details = MagicMock(
        return_value=[{"reason": "Resolved - False Positive"}]
    )

    mock_incident: IncidentInfo = get_mock_incident()
    palo_alto_cortex_xdr.add_incidents([mock_incident])
    palo_alto_cortex_xdr.add_incident_extra_data(
        get_mock_incident_extra_data(mock_incident)
    )

    mock_case_object = get_mock_case_details()
    mock_case_object.identifier = MOCK_CASE_IDENTIFIER
    palo_alto_cortex_xdr.add_case_overview_details([mock_case_object])

    # pylint: disable=protected-access
    original_initialize_run = soar_job._initialize_run

    def initialize_run_patch():
        soar_job.params.max_hours_backwards = int(soar_job.params.max_hours_backwards)
        original_initialize_run()

    # pylint: disable=protected-access
    with patch.object(
        soar_job,
        "_initialize_run",
        side_effect=initialize_run_patch,
    ):
        with patch.object(soar_job.logger, "info") as mock_logger_info:
            soar_job.start()

            log_messages: list[str] = [
                call.args[0] for call in mock_logger_info.call_args_list
            ]
            assert len(soar_sdk_session.request_history) == 2
            assert any("Successfully synced" in message for message in log_messages)


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_job_runs_no_cases_found(
    soar_sdk_session: PaloAltoCortexXDRSOARSession,
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
) -> None:
    soar_job: SyncIncidents = SyncIncidents()
    mock_soar_job_for_run(soar_job)

    mock_incident: IncidentInfo = get_mock_incident()
    palo_alto_cortex_xdr.add_incidents([mock_incident])
    palo_alto_cortex_xdr.add_incident_extra_data(
        get_mock_incident_extra_data(mock_incident)
    )

    mock_case_object = get_mock_case_details()
    mock_case_object.identifier = MOCK_CASE_IDENTIFIER
    palo_alto_cortex_xdr.add_case_overview_details([mock_case_object])

    # pylint: disable=protected-access
    soar_job._get_case_ids_by_timestamp.return_value = []

    # pylint: disable=protected-access
    original_initialize_run = soar_job._initialize_run

    def initialize_run_patch():
        soar_job.params.max_hours_backwards = int(soar_job.params.max_hours_backwards)
        original_initialize_run()

    # pylint: disable=protected-access
    with patch.object(
        soar_job,
        "_initialize_run",
        side_effect=initialize_run_patch,
    ):
        with patch.object(soar_job.logger, "info") as mock_logger_info:
            soar_job.start()

            log_messages: list[str] = [
                call.args[0] for call in mock_logger_info.call_args_list
            ]
            assert len(soar_sdk_session.request_history) == 1
            assert any(
                "No new/modified cases found" in message for message in log_messages
            )
