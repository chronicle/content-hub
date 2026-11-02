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

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.validation import ParameterValidator
from crowd_strike_falcon.core import constants
from crowd_strike_falcon.core import exceptions
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.datamodels import AlertDetails


class UpdateAlertAction(Action):

    def __init__(self) -> None:
        super().__init__(constants.UPDATE_ALERT_SCRIPT_NAME)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{constants.UPDATE_ALERT_SCRIPT_NAME}".'
        )
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        # TODO(b/285819111): Extract this to a function so all scripts could use it
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API Root",
            is_mandatory=True,
        )
        self.params.client_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client API ID",
            is_mandatory=True,
        )
        self.params.client_secret = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client API Secret",
            is_mandatory=True,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            is_mandatory=True,
        )
        self.params.customer_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Customer ID",
            print_value=True,
        )

        self.params.alert_id = extract_action_param(
            self.soar_action, param_name="Alert ID", is_mandatory=True, print_value=True
        )
        self.params.status = extract_action_param(
            self.soar_action,
            param_name="Status",
            default_value=constants.DDL_PARAM_DEFAULT_VALUE,
            print_value=True,
        )
        self.params.verdict = extract_action_param(
            self.soar_action,
            param_name="Verdict",
            default_value=constants.DDL_PARAM_DEFAULT_VALUE,
            print_value=True,
        )
        self.params.assign_to = extract_action_param(
            self.soar_action, param_name="Assign To", print_value=True
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        validator.validate_ddl(
            param_name="Status",
            value=self.params.status,
            ddl_values=constants.STATUS_VALUES,
            default_value=constants.DDL_PARAM_DEFAULT_VALUE,
        )
        validator.validate_ddl(
            param_name="Verdict",
            value=self.params.verdict,
            ddl_values=constants.VERDICT_MAPPING,
            default_value=constants.DDL_PARAM_DEFAULT_VALUE,
        )

        error_message = (
            "at least one of the  “Status” or “Assign To” or “Verdict” parameters "
            "should have a value ."
        )
        if (self.params.status == constants.DDL_PARAM_DEFAULT_VALUE) and (
            not self.params.assign_to
        ):
            raise exceptions.CrowdStrikeParameterError(error_message)

    def _init_api_clients(self) -> CrowdStrikeManager:
        """Initializing CrowdStrikeManager.

        Returns:
            CrowdStrikeManager: CrowdStrikeManager instance.
        """
        return CrowdStrikeManager(
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            use_ssl=self.params.verify_ssl,
            api_root=self.params.api_root,
            customer_id=self.params.customer_id,
        )

    def _perform_action(self, _) -> None:
        self.logger.info("Validating Alert ID")
        self._fetch_alert()
        self._update_alert()
        alert_details = self._fetch_alert()
        self._set_action_result(alert_details)

    def _fetch_alert(self) -> list[AlertDetails]:
        try:
            return self.api_client.get_alerts_details(ids=[self.params.alert_id])
        except (
            exceptions.CrowdStrikeNotFoundError,
            exceptions.CrowdStrikeBadRequestError,
        ) as err:
            raise exceptions.AlertNotFoundException(
                f"alert with ID {self.params.alert_id} wasn’t found in Crowdstrike."
                " Please check the spelling."
            ) from err

        return []

    def _update_alert(self) -> None:
        self.api_client.update_alert(
            alert_id=self.params.alert_id,
            status=self.params.status,
            verdict=self.params.verdict,
            assign_to=self.params.assign_to,
        )

    def _set_action_result(self, alert_details: list[AlertDetails]) -> None:
        self.json_results = alert_details[0].to_json()
        self.output_message = (
            f"Successfully updated alert with ID {self.params.alert_id} in Crowdstrike."
        )


def main() -> None:
    UpdateAlertAction().run()


if __name__ == "__main__":
    main()
