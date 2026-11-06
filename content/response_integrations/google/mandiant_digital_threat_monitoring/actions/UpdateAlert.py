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
import requests

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator
from ..core import api_utils
from ..core import constants
from ..core import AuthenticationManager as auth_manager
from ..core import MandiantDTMManager as api_manager
from ..core.exceptions import MandiantDTMBadRequestException


class UpdateAlert(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.json_results = {}
        self.output_message = (
            f"Successfully connected to the {constants.PROVIDER_NAME} server with the "
            f"provided connection parameters!"
        )
        self.error_output_message = (
            f"Error executing action " f'"{constants.UPDATE_ALERT_NAME}".'
        )

    def _extract_parameters(self) -> None:
        integration_params = api_utils.get_integration_params(self.soar_action)
        self.params.session_auth_params = integration_params.auth_params
        self.params.api_params = integration_params.api_params

        self.params.alert_id = extract_action_param(
            self.soar_action, param_name="Alert ID", is_mandatory=True, print_value=True
        )

        self.params.alert_status = extract_action_param(
            self.soar_action, param_name="Status", is_mandatory=False, print_value=True
        )
        self.params.alert_status = constants.ALERT_STATUS_MAPPING.get(
            self.params.alert_status
        )

    def _validate_params(self) -> None:
        if self.params.alert_status is None:
            raise MandiantDTMBadRequestException(
                '"Status" parameter should have a value.'
            )
        validator = ParameterValidator(self.soar_action)
        values = [v for v in constants.ALERT_STATUS_MAPPING.values() if v is not None]
        validator.validate_ddl(
            param_name="Status", value=self.params.alert_status, ddl_values=values
        )

    def _init_managers(self) -> api_manager.ApiManager:
        session = self._get_authenticated_session()
        return api_manager.ApiManager(
            session=session,
            api_params=self.params.api_params,
            logger=self.soar_action.LOGGER,
            gti_api_key=self.params.session_auth_params.gti_api_key,
        )

    def _get_authenticated_session(self) -> requests.Session:
        return auth_manager.get_authenticated_session(self.params.session_auth_params)

    def _perform_action(self, manager: api_manager.ApiManager) -> None:
        response = manager.update_alert(self.params.alert_id, self.params.alert_status)
        api_utils.validate_response(response)
        self.json_results = response.json()
        self.output_message = (
            f"Successfully updated alert with ID {self.params.alert_id} in "
            f"{constants.PROVIDER_NAME}."
        )


def main() -> None:
    UpdateAlert(constants.UPDATE_ALERT_NAME).run()


if __name__ == "__main__":
    main()
