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

import base64
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator
from palo_alto_cortex_xdr.core import action_init
from palo_alto_cortex_xdr.core.base_action import BaseAction
from palo_alto_cortex_xdr.core import constants
from palo_alto_cortex_xdr.core import datamodels

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import SingleJson

    from palo_alto_cortex_xdr.core.XDRManager import XDRManager


SUCCESS_MESSAGE: str = (
    "Successfully returned information about incident with ID {incident_id} in "
    f"{constants.VENDOR} {constants.PRODUCT}."
)


class GetIncidentDetails(BaseAction):
    def __init__(self) -> None:
        super().__init__(constants.GET_INCIDENT_DETAILS_ACTION_SCRIPT_NAME)
        self.error_output_message: str = (
            "Error executing action "
            f'"{constants.GET_INCIDENT_DETAILS_ACTION_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.incident_id = extract_action_param(
            self.soar_action,
            param_name="Incident ID",
            print_value=True,
        )
        self.params.severity = extract_action_param(
            self.soar_action,
            param_name="Lowest Alert Severity",
            default_value=constants.XDRPriorityEnum.HIGH.value.title(),
            print_value=True,
        )
        self.params.max_results = extract_action_param(
            self.soar_action,
            param_name="Max Alerts To Return",
            is_mandatory=True,
            default_value=constants.XQL_DEFAULT_LIMIT,
            print_value=True,
            input_type=int,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(siemplify=self.soar_action)
        validator.validate_ddl(
            param_name="Lowest Alert Severity",
            value=self.params.severity,
            ddl_values=[
                severity.value.title() for severity in constants.XDRPriorityEnum
            ],
        )
        validator.validate_range(
            param_name="Max Alerts To Return",
            value=self.params.max_results,
            min_limit=1,
            max_limit=constants.MAX_LIMIT,
        )

    def _init_api_clients(self) -> XDRManager:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        incident: list[datamodels.Alert] = self._get_incident_details()
        self._set_action_result(incident)

    def _get_incident_details(self) -> list[datamodels.Alert]:
        return self.api_client.get_incident_details(
            incident_id=self.params.incident_id,
            limit=self.params.max_results,
        )

    def _set_action_result(self, incident: datamodels.Incident) -> None:
        self.json_results = self._get_json_result(incident)
        self.output_message = SUCCESS_MESSAGE.format(
            incident_id=self.params.incident_id,
        )

    def _get_json_result(self, incident: datamodels.Incident) -> SingleJson:
        json_result: SingleJson = incident.to_json()
        json_result.pop("alerts", None)
        incident_data: SingleJson = json_result.pop("incident")
        incident_data["network_artifacts"] = json_result.pop("network_artifacts", None)
        incident_data["file_artifacts"] = json_result.pop("file_artifacts", None)
        incident_data["alerts"] = [
            alert.to_json()
            for alert in incident.alerts
            if _alert_passes_min_severity(
                alert=alert, lowest_severity=self.params.severity
            )
        ]

        return incident_data


def _alert_passes_min_severity(
    alert: datamodels.Alert,
    lowest_severity: str,
) -> bool:
    try:
        min_severity_index = constants.SEVERITY_ORDER.index(lowest_severity.lower())
        alert_severity_index = constants.SEVERITY_ORDER.index(alert.severity)
        return min_severity_index <= alert_severity_index

    except ValueError:
        return False


def main() -> NoReturn:
    GetIncidentDetails().run()


if __name__ == "__main__":
    main()
