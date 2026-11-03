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
from microsoft_graph_security.core import constants
from microsoft_graph_security.core import exceptions
from microsoft_graph_security.core.MicrosoftGraphSecurityManager import MicrosoftGraphSecurityManager


class AddAlertComment(Action):

    def __init__(self) -> None:
        super().__init__(constants.ADD_ALERT_COMMENT_SCRIPT_NAME)
        self.output_message = ""
        self.result_value = False
        self.error_output_message = (
            f'Error executing action "{constants.ADD_ALERT_COMMENT_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.client_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client ID",
            is_mandatory=True,
        )
        self.params.secret_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Secret ID",
        )
        self.params.certificate_path = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Certificate Path",
        )
        self.params.certificate_password = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Certificate Password",
        )
        self.params.tenant = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Tenant",
            is_mandatory=True,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            default_value=False,
            print_value=True,
        )
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API Root",
            default_value=constants.DEFAULT_API_ROOT,
            print_value=True,
        )
        self.params.login_api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Login API Root",
            default_value=constants.DEFAULT_LOGIN_API_ROOT,
            print_value=True,
        )

        # Action parameters
        self.params.alert_id = extract_action_param(
            self.soar_action,
            param_name="Alert ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        if len(self.params.comment) > constants.API_COMMENT_LIMITATION:
            raise exceptions.ActionParameterValidationError(
                "Comment length cannot be greater than "
                f"{constants.API_COMMENT_LIMITATION} characters"
            )

    def _init_api_clients(self) -> MicrosoftGraphSecurityManager:
        return MicrosoftGraphSecurityManager(
            client_id=self.params.client_id,
            client_secret=self.params.secret_id,
            certificate_path=self.params.certificate_path,
            certificate_password=self.params.certificate_password,
            tenant=self.params.tenant,
            verify_ssl=self.params.verify_ssl,
            api_root=self.params.api_root,
            login_api_root=self.params.login_api_root,
            siemplify=self.soar_action,
        )

    def _perform_action(self, _) -> None:
        try:
            self.api_client.add_comment_to_alert(
                alert_id=self.params.alert_id,
                comment=self.params.comment
            )
            self.result_value = True
            self.output_message = (
                "Successfully added comment to the alert "
                f"{self.params.alert_id} in Microsoft Graph"
            )

        except exceptions.MicrosoftGraphSecurityManagerError as error:
            raise exceptions.AlertNotFoundException(
                f"alert with ID {self.params.alert_id} wasn't found in "
                "MicrosoftGraphSecurity. Please check the spelling."
            ) from error


def main() -> NoReturn:
    AddAlertComment().run()


if __name__ == "__main__":
    main()
