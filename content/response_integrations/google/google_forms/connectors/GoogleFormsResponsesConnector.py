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

from typing import NoReturn

from collections import defaultdict
from itertools import chain

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.data_models import BaseAlert
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from TIPCommon.types import SingleJson
from ..core import constants
from ..core import datamodels
from ..core import exceptions
from ..core.GoogleFormsAuth import build_auth_manager_params, GoogleFormsAuthManager
from ..core.GoogleFormsManager import GoogleFormsManager


class ResponseConnector(Connector):

    def __init__(self) -> None:
        super().__init__(constants.RESPONSE_CONNECTOR_NAME)
        self.manager: GoogleFormsManager | None = None
        self.context_data = defaultdict(
            lambda: {"tracked_responses": [], "lastResponseCreatedTime": None}
        )
        self.last_alert_time_per_form = {}
        self.existing_last_alert_time_per_form = {}

    def validate_params(self) -> None:
        """Validate connector params with param_validator."""

        if self.params.alert_severity not in constants.ALLOWED_SEVERITIES:
            raise exceptions.InvalidParameterException(
                'Invalid parameter "Alert Severity". possible values are '
                f"{convert_list_to_comma_string(constants.ALLOWED_SEVERITIES)}"
            )

        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )

        self.params.max_responses_to_fetch = self.param_validator.validate_positive(
            param_name="Max Responses To Fetch",
            value=self.params.max_responses_to_fetch,
            default_value=constants.PAGESIZE,
        )

    def init_managers(self) -> None:
        auth_manager_params = build_auth_manager_params(self.siemplify)
        auth_manager = GoogleFormsAuthManager(auth_manager_params)

        self.manager = GoogleFormsManager(
            auth_manager.prepare_session(),
            datamodels.IntegrationParameters(siemplify_logger=self.logger),
        )

    def read_context_data(self) -> None:
        """
        Reads and processes existing alert IDs and last response times from the context.
        """
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)
        for form in self.context.existing_ids:
            for form_id, value in form.items():
                self.existing_last_alert_time_per_form[form_id] = value.get(
                    "lastResponseCreatedTime"
                )

    def get_last_success_time(self, **kwargs) -> int:
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            time_format=UNIX_FORMAT,
            **kwargs,
        )

    def get_alerts(self) -> list[datamodels.AlertResponse.get_alert_info]:
        """Retrieve alerts from Google Forms based on specified tracking and
            filtering criteria.

        Returns:
            list[datamodels.AlertResponse.get_alert_info]: A list of processed alert
                information objects.
        """
        alerts = []
        self.params.form_i_ds_to_track = string_to_multi_value(
            self.params.form_i_ds_to_track,
            only_unique=True,
        )

        for form_id in self.params.form_i_ds_to_track:
            last_alert_time = (
                self.existing_last_alert_time_per_form.get(form_id)
                or self.context.last_success_timestamp
            )
            alert = self.manager.get_forms(
                form_id=form_id,
                max_alerts_to_fetch=self.params.max_responses_to_fetch,
                max_hours_backwards=self.params.max_hours_backwards,
                last_alert_time=last_alert_time,
            )

            if alert:
                alerts.extend(alert)
                self._set_last_timestamp_per_form(alert)

        self.validate_alerts()

        return alerts

    def _set_last_timestamp_per_form(
        self,
        alerts: list[datamodels.AlertResponse],
    ) -> None:
        latest_alert = sorted(alerts, key=lambda x: x.create_time, reverse=True)[0]
        self.last_alert_time_per_form[latest_alert.form_id] = latest_alert.create_time

    def validate_alerts(self) -> None:
        """Validates the alerts by checking if the form IDs in the alerts match the
        form IDs to track.
        """
        form_ids = []
        for ids in self.params.form_i_ds_to_track:
            form_id = self.manager.get_forms_detail(form_id=ids)
            if form_id:
                form_ids.append(form_id.form_id)

        failed_ids = convert_list_to_comma_string(
            list(set(form_ids) ^ set(self.params.form_i_ds_to_track))
        )
        if len(form_ids) == 0:
            raise exceptions.InvalidFormIdsException(
                "there should be at least 1 valid form ID provided."
            )

        if failed_ids:
            self.logger.info(f'Form "{failed_ids}" wasn’t found. Skipping…')

    def max_alerts_processed(self, processed_alerts: list[AlertInfo]) -> bool:
        """
        Return True if reached the maximum alerts to process limit in
        the connector execution.

        Args:
            processed_alerts list[AlertInfo]: A list of processed alerts.

        Returns:
            True if the maximum alerts to process limit has been reached,
            False otherwise.
        """
        alerts_to_process = self.params.max_responses_to_fetch * len(
            self.params.form_i_ds_to_track
        )
        if len(processed_alerts) >= alerts_to_process:
            return True

        return False

    def process_alert(
        self,
        alert: datamodels.AlertResponse,
    ) -> list[SingleJson]:
        """Processes an alert and returns its associated events.

        Args:
            alert (datamodels.AlertResponse): The alert object to be processed.

        Returns:
            list[SingleJson]: A list of JSON objects representing the alert's events.
        """
        alert.set_events()
        return alert

    def filter_alerts(
        self,
        fetched_alerts: list[BaseAlert],
    ) -> list[datamodels.AlertResponse.get_alert_info]:
        """Filters the fetched alerts by excluding those already processed
            (based on their IDs).

        Args:
            fetched_alerts (list[BaseAlert]): List of alerts to filter.

        Returns:
            list[datamodels.AlertResponse.get_alert_info]: A list of filtered alerts.
        """
        filtered_alerts = []
        existing_alert_ids = self.get_existing_alert_ids()
        for alert in fetched_alerts:
            ids = getattr(alert, "alert_id")

            if ids not in existing_alert_ids:
                filtered_alerts.append(alert)
            else:
                self.logger.info(
                    f"The alert {ids} skipped since it has been fetched before."
                )

        return filtered_alerts

    def get_existing_alert_ids(self) -> list[str]:
        return list(
            chain.from_iterable(
                form_data.get("tracked_responses", [])
                for alerts_data in self.context.existing_ids
                for form_data in alerts_data.values()
            )
        )

    def store_alert_in_cache(
        self,
        processed_alert: datamodels.AlertResponse,
    ) -> None:
        """Save alert id to `ids.json` or equivalent.

        Args:
            processed_alert (datamodels.AlertResponse): The alert with id to store.
        """
        self.context_data[processed_alert.form_id]["tracked_responses"].append(
            processed_alert.alert_id
        )
        self.context_data[processed_alert.form_id]["lastResponseCreatedTime"] = (
            self.last_alert_time_per_form[processed_alert.form_id]
        )

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        return not self.params.disable_overflow and super().is_overflow_alert(
            alert_info
        )

    def create_alert_info(self, processed_alert: datamodels.AlertResponse) -> AlertInfo:
        return processed_alert.get_alert_info(
            alert_info=AlertInfo(),
            environment_common=self.env_common,
            severity=self.params.alert_severity,
        )

    def set_last_success_time(
        self, alerts: list[datamodels.AlertResponse.get_alert_info], **kwargs
    ) -> None:
        """Set connector's last success time."""
        for alert_list in alerts:
            if isinstance(alert_list, datamodels.AlertResponse):
                alert_list = [alert_list]

            super().set_last_success_time(
                alerts=alert_list,
                timestamp_key="create_time",
                **kwargs,
            )

    def write_context_data(
        self, alerts: list[datamodels.AlertResponse.get_alert_info]
    ) -> None:
        """Write connector's context data."""
        if not alerts:
            return

        self.logger.info("Saving existing ids.")
        write_ids(self.siemplify, self.set_context_data_ids())

    def set_context_data_ids(self) -> list[SingleJson]:
        """Merges new form responses into existing responses, handling updates and
        additions.

        Returns:
            list[SingleJson]: A new list of dictionaries containing the merged and
            updated response data.
        """

        merged_responses = {}

        self._add_responses_to_dict(merged_responses)
        self._update_or_add_new_responses(merged_responses)

        return self._convert_form_data_to_context(merged_responses)

    def _add_responses_to_dict(self, response_dict: SingleJson) -> None:
        for form_data in self.context.existing_ids:
            for form_id, data in form_data.items():
                response_dict[form_id] = data

    def _update_or_add_new_responses(self, response_dict: SingleJson) -> None:
        for form_id, data in self.context_data.items():
            if form_id in response_dict:
                response_dict[form_id]["tracked_responses"].extend(
                    data["tracked_responses"]
                )
                response_dict[form_id]["lastResponseCreatedTime"] = data[
                    "lastResponseCreatedTime"
                ]
            else:
                response_dict[form_id] = data

    def _convert_form_data_to_context(
        self,
        response_dict: SingleJson,
    ) -> list[SingleJson]:
        return [{form_id: data} for form_id, data in response_dict.items()]


def main() -> NoReturn:
    ResponseConnector().start()


if __name__ == "__main__":
    main()
