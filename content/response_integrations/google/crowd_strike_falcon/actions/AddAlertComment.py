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

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.validation import ParameterValidator
from crowd_strike_falcon.core import constants
from crowd_strike_falcon.core import exceptions
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager


class AddAlertComment(Action):

    def __init__(self) -> None:
        super().__init__(constants.ADD_ALERT_COMMENT_SCRIPT_NAME)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{constants.ADD_ALERT_COMMENT_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        # Configuration Parameters
        # TODO(b/285819111): Extract this to a function so all scripts could use it
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API Root",
            default_value=constants.API_ROOT_DEFAULT,
        )
        self.params.client_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client API ID",
        )
        self.params.client_secret = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client API Secret",
        )
        self.params.use_ssl = extract_configuration_param(
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

        # Action parameters
        self.params.alert_id = extract_action_param(
            self.soar_action, param_name="Alert ID", is_mandatory=True, print_value=True
        )
        self.params.comment = extract_action_param(
            self.soar_action, param_name="Comment", is_mandatory=True, print_value=True
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        error_message = (
            "Invalid action value specified, must be less than or equal to 1024 "
            "characters."
        )
        validator.validate_upper_limit(
            param_name="Comment",
            value=len(self.params.comment),
            limit=constants.COMMENT_CHAR_LENGTH_LIMIT,
            print_error=error_message,
        )

    def _init_api_clients(self) -> CrowdStrikeManager:
        return CrowdStrikeManager(
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            use_ssl=self.params.use_ssl,
            api_root=self.params.api_root,
            customer_id=self.params.customer_id,
        )

    def _perform_action(self, _) -> None:
        self._validate_alert_id(alert_id=self.params.alert_id)
        self._add_comment_to_alert(
            alert_id=self.params.alert_id, comment=self.params.comment
        )

    def _validate_alert_id(self, alert_id: str) -> None:
        try:
            self.api_client.get_alerts_details([alert_id])

        except (
            exceptions.CrowdStrikeSessionCreatedError,
            exceptions.CrowdStrikeBadRequestError,
        ) as error:
            raise exceptions.AlertNotFoundException(
                f"alert with ID {alert_id} wasn't found in Crowdstrike. "
                "Please check the spelling."
            ) from error

    def _add_comment_to_alert(
        self, alert_id: str, comment: str) -> None:
        self.api_client.add_comment_to_alert(alert_id=alert_id, comment=comment)
        self.output_message = (
            "Successfully added comment to the alert with ID "
            f"{alert_id} in Crowdstrike."
        )


def main() -> NoReturn:
    AddAlertComment().run()


if __name__ == "__main__":
    main()
