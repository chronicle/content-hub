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

import requests

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.types import SingleJson
from TIPCommon.validation import ParameterValidator
from ..core import constants
from ..core import exceptions
from ..core import api_utils
from ..core import AuthenticationManager as auth_manager
from ..core import PaloAltoPrismaCloudManager as api_manager


class RespondToAlertAction(Action):

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{constants.RESPOND_TO_ALERT_SCRIPT_NAME}".'
        )
        self.json_results = {}

    def _extract_parameters(self) -> None:
        integration_params = api_utils.get_integration_params(self.soar_action)
        self.params.session_auth_params = integration_params.auth_params
        self.params.api_params = integration_params.api_params

        self.params.alert_id = extract_action_param(
            self.soar_action, param_name="Alert ID", is_mandatory=True, print_value=True
        )
        self.params.response_type = extract_action_param(
            self.soar_action,
            param_name="Response Type",
            print_value=True,
            default_value=constants.DEFAULT_RESPONSE_TYPE,
        )
        self.params.dismiss_note = extract_action_param(
            self.soar_action, param_name="Dismiss Note", print_value=True
        )
        self.params.Snooze_time = extract_action_param(
            self.soar_action, param_name="Snooze Time", print_value=True
        )

    def _init_managers(self) -> api_manager.ApiManager:
        session = self._get_authenticated_session()
        return api_manager.ApiManager(
            session=session,
            api_parameters=self.params.api_params,
            logger=self.soar_action.LOGGER,
        )

    def _get_authenticated_session(self) -> requests.Session:
        return auth_manager.get_authenticated_session(self.params.session_auth_params)

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        validator.validate_ddl(
            param_name="Response Type",
            value=self.params.response_type,
            ddl_values=constants.RESPONSE_TYPE,
        )

    def _validate_response_type(self) -> None:
        if self.params.response_type == constants.DEFAULT_RESPONSE_TYPE:
            raise exceptions.InvalidParameterException(
                "The Response Type parameter is misconfigured. Select a valid"
                " value for the Response Type parameter."
            )

    def __verify_alert_id(self, manager: api_manager.ApiManager) -> None:
        error_message = (
            f"Alert with ID {self.params.alert_id} wasn’t found in "
            f"{constants.INTEGRATION_DISPLAY_NAME}. Please check the spelling."
        )
        manager.verify_alert(alert_id=self.params.alert_id, error_message=error_message)

    def _respond_to_alert(self, manager: api_manager.ApiManager) -> SingleJson:
        error_message = (
            f"Action couldn’t respond to alert with ID {self.params.alert_id} "
            f"{constants.INTEGRATION_DISPLAY_NAME}. Please check the action "
            "configuration parameters."
        )
        respond_status = manager.respond_to_alert(
            alert_id=self.params.alert_id,
            response_type=self.params.response_type,
            dismissal_note=self.params.dismiss_note,
            snooze_time=self.params.Snooze_time,
            error_message=error_message,
        )
        return respond_status

    def _validate_snooze_time(self) -> None:
        if self.params.response_type == "Snooze" and self.params.Snooze_time is None:
            raise exceptions.InvalidParameterException(
                "The Response Type parameter was set to “Snooze”. Make sure that"
                " the Snooze Time parameter value is configured and valid."
            )

    def _perform_action(self, manager: api_manager.ApiManager, _=None) -> None:
        self.logger.info(
            f"Successfully connected to {constants.INTEGRATION_DISPLAY_NAME}"
        )
        self.__verify_alert_id(manager)
        self.logger.info("Alert ID has been verified")
        self._validate_response_type()
        self._validate_snooze_time()
        respond_status = self._respond_to_alert(manager)
        self._set_action_result(self.params.alert_id, respond_status)

    def _set_action_result(self, alert_id: str, alert_status: SingleJson) -> None:
        self.json_results = alert_status
        self.output_message = (
            f"Successfully responded to an alert with ID {alert_id} in "
            "Palo Alto Prisma Cloud"
        )


def main() -> NoReturn:
    action = RespondToAlertAction(constants.RESPOND_TO_ALERT_SCRIPT_NAME)
    action.run()


if __name__ == "__main__":
    main()
