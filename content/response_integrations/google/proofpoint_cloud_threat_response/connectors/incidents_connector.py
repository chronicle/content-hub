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

import sys
from datetime import datetime
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.filters import filter_old_alerts
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.utils import is_overflowed, is_test_run
from TIPCommon.validation import ParameterValidator
from proofpoint_cloud_threat_response.core import constants
from proofpoint_cloud_threat_response.core.api_client import ApiParameters, ProofpointCloudThreatResponseApiClient
from proofpoint_cloud_threat_response.core.auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
    build_auth_params,
)
from proofpoint_cloud_threat_response.core.exceptions import ProofpointCTRError, ProofpointCTRRateLimitError
from proofpoint_cloud_threat_response.core.data_models import ProofpointIncident, ProofpointIncidentAlertInfo

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class ProofpointCTRIncidentsConnector(Connector):
    def __init__(self, is_test_connector_run: bool) -> None:
        super().__init__(constants.CONNECTOR_SCRIPT_NAME, is_test_connector_run)
        self.manager: ProofpointCloudThreatResponseApiClient | None = None

    def validate_params(self) -> None:
        """Validates params."""
        validator: ParameterValidator = ParameterValidator(self.siemplify)
        validator.validate_csv(
            param_name="Lowest Severity To Fetch",
            csv_string=self.params.lowest_severity_to_fetch,
            possible_values=list(constants.SEVERITY_MAP.keys()),
        )
        validator.validate_csv(
            param_name="Lowest Confidence To Fetch",
            csv_string=self.params.lowest_confidence_to_fetch,
            possible_values=list(constants.CONFIDENCE_MAP.keys()),
        )
        validator.validate_csv(
            param_name="Status Filter",
            csv_string=self.params.status_filter,
            possible_values=list(constants.STATUS_MAP.keys()),
        )
        validator.validate_csv(
            param_name="Disposition Filter",
            csv_string=self.params.disposition_filter,
            possible_values=list(constants.DISPOSITION_MAP.keys()),
        )
        validator.validate_csv(
            param_name="Verdict Filter",
            csv_string=self.params.verdict_filter,
            possible_values=list(constants.VERDICT_MAP.keys()),
        )
        validator.validate_lower_limit(
            param_name="Max Hours Backwards",
            value=self.params.max_hours_backwards,
            limit=constants.MIN_INT_PARAM_LIMIT,
        )
        validator.validate_range(
            param_name="Max Incidents To Fetch",
            value=self.params.max_incidents_to_fetch,
            min_limit=constants.MIN_INT_PARAM_LIMIT,
            max_limit=constants.MAX_INCIDENTS_LIMIT,
        )

    def init_managers(self) -> ProofpointCloudThreatResponseApiClient:
        """Api client for proofpoint cloud threat response."""
        auth_params = build_auth_params(self.siemplify)
        authenticator: AuthenticatedSession = AuthenticatedSession()
        auth_params_for_session = SessionAuthenticationParameters(
            client_id=auth_params.client_id,
            client_secret=auth_params.client_secret,
            auth_url=constants.AUTH_URL,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(auth_params_for_session)
        authenticated_session: AuthenticatedSession = authenticator.session

        api_params: ApiParameters = ApiParameters(
            api_root=auth_params.api_root,
        )

        self.manager = ProofpointCloudThreatResponseApiClient(
            authenticated_session=authenticated_session,
            configuration=api_params,
            logger=self.logger,
        )
        return self.manager

    def read_context_data(self) -> None:
        self.logger.info("Reading existing incident ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def get_last_success_time(self) -> datetime:
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
        )

    def get_alerts(self) -> list[AlertInfo]:
        """ Gets the alerts to be ingest to soar instance."""
        alerts: list[AlertInfo] = []
        incidents: list[ProofpointIncident] = []

        now = datetime.utcnow()
        end_row = min(
            constants.MAX_INCIDENTS_LIMIT,
            int(
                self.params.max_incidents_to_fetch,
            ),
        )

        filters: SingleJson = {}
        if priority_filters := _build_priority_filters(
            self.params.lowest_severity_to_fetch
        ):
            filters["priority_filters"] = priority_filters
        if confidence_filters := _build_confidence_filters(
            self.params.lowest_confidence_to_fetch
        ):
            filters["confidence_filters"] = confidence_filters
        if disposition_filters := _map_disposition_filters(
            self.params.disposition_filter
        ):
            filters["disposition_filters"] = disposition_filters
        if verdict_filters := _map_verdict_filters(self.params.verdict_filter):
            filters["verdict_filters"] = verdict_filters
        try:
            incidents = self.manager.list_incidents(
                start_time=self.context.last_success_timestamp,
                end_time=now,
                end_row=end_row,
                filters=filters,
            )
            requested_statuses: set[str] = _get_requested_statuses(
                self.params.status_filter,
            )
            incidents = [
                incident
                for incident in incidents
                if incident.status in requested_statuses
            ]
            self.logger.info(
                f"Fetched {len(incidents)} incidents after status filtering: "
                f"{', '.join(requested_statuses)}"
            )

        except ProofpointCTRRateLimitError as e:
            self.logger.error(
                f"Rate limit error occurred while fetching incidents: {e}"
            )

        for incident in incidents:
            try:
                messages = self.manager.get_incident_messages(incident.id_)
                alert = ProofpointIncidentAlertInfo.build_alert(
                    incident=incident,
                    messages_raw_list=messages,
                    env_common=self.env_common,
                    environment_field_name=getattr(
                        self.params, "environment_field_name", None
                    ),
                )

                alerts.append(alert)

            except (ProofpointCTRError, ProofpointCTRRateLimitError) as e:
                self.logger.error(f"Failed to process incident {incident.id_}: {e}")

        return alerts

    def filter_alerts(self, alerts: list[AlertInfo]) -> list[AlertInfo]:
        return filter_old_alerts(
            self.siemplify,
            alerts,
            self.context.existing_ids,
        )

    def max_alerts_processed(self, processed_alerts: list[AlertInfo]) -> bool:
        return len(processed_alerts) >= int(self.params.max_incidents_to_fetch)

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        return not self.params.disable_overflow and is_overflowed(
            self.siemplify, alert_info, self.is_test_run
        )

    def pass_filters(self, alert: AlertInfo) -> bool:
        return alert.pass_filter(
            self.siemplify,
            self.params.use_dynamic_list_as_a_blocklist,
        )

    def store_alert_in_cache(self, alert: AlertInfo) -> None:
        self.context.existing_ids.append(alert.alert_id)

    def create_alert_info(self, alert: AlertInfo) -> AlertInfo:
        return alert

    def set_last_success_time(self, alerts: list[AlertInfo]) -> None:
        super().set_last_success_time(
            alerts=alerts,
            timestamp_key="start_time",
        )

    def write_context_data(self, all_alerts: list[AlertInfo]) -> None:
        """Writes the context to the db."""
        if not all_alerts:
            return

        self.logger.info(f"Saving {len(self.context.existing_ids)} incident ids.")
        write_ids(self.siemplify, self.context.existing_ids)


def _get_requested_statuses(csv_values: str | None) -> set[str]:
    if not csv_values:
        return {constants.STATUS_MAP["Open"]}

    requested = {
        constants.STATUS_MAP[key]
        for key in string_to_multi_value(csv_values, only_unique=True)
        if key in constants.STATUS_MAP
    }

    return requested


def _map_disposition_filters(csv_values: str | None) -> list[str] | None:
    if not csv_values:
        return None

    result: list[str] = []
    for key in string_to_multi_value(csv_values, only_unique=True):
        if mapped := constants.DISPOSITION_MAP.get(key):
            result.append(mapped)

    return result or None


def _map_verdict_filters(csv_values: str | None) -> list[str] | None:
    if not csv_values:
        return None

    result: list[str] = []
    for key in string_to_multi_value(csv_values, only_unique=True):
        if mapped := constants.VERDICT_MAP.get(key):
            result.append(mapped)

    return result or None


def _build_priority_filters(value: str | None) -> list[str] | None:
    if not value:
        return None

    return constants.SEVERITY_MAP.get(value)


def _build_confidence_filters(value: str | None) -> list[str] | None:
    if not value:
        return None

    return constants.CONFIDENCE_MAP.get(value)


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = ProofpointCTRIncidentsConnector(is_test)
    connector.start()
