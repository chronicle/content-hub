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

from typing import Any, NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator
from ..core import action_init
from ..core import constants
from ..core import datamodels
from ..core import exceptions
from ..core import utils


class ActivateNetworkList(Action):

    def __init__(self) -> None:
        super().__init__(constants.ACTIVATE_NETWORK_LIST_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False

    def _extract_action_parameters(self) -> None:
        self.params.network_list_name = extract_action_param(
            self.soar_action,
            param_name="Network List Name",
            print_value=True,
        )
        self.params.network_list_id = extract_action_param(
            self.soar_action,
            param_name="Network List ID",
            print_value=True,
        )
        self.params.environment = extract_action_param(
            self.soar_action,
            param_name="Environment",
            default_value="Production",
            print_value=True,
        )
        self.params.comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            print_value=True,
        )
        self.params.notification_recipients = extract_action_param(
            self.soar_action,
            param_name="Notification Recipients",
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        if not (self.params.network_list_name or self.params.network_list_id):
            raise exceptions.AkamaiManagerError(
                'Provide a value in "Network List Name" or '
                '"Network List ID" parameter.',
            )

        self.params.environment = validator.validate_ddl(
            param_name="Environment",
            value=self.params.environment,
            ddl_values=constants.ACTIVATION_ENVIRONMENTS,
        )

        if self.params.notification_recipients:
            validator.validate_csv(
                param_name="Notification Recipients",
                csv_string=self.params.notification_recipients,
            )

    def _init_api_clients(self) -> None:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _: Any = None) -> None:
        try:
            network_list_id_to_activate = self._get_network_list_id()
            recipients: list[str] = string_to_multi_value(
                string_value=self.params.notification_recipients,
            )
            api_environment = constants.API_ENVIRONMENTS.get(self.params.environment)

            activation_result = self._activate_list_via_api(
                network_list_id_to_activate,
                api_environment,
                recipients,
            )
            self._process_successful_activation(activation_result)
        except (exceptions.AuthenticationError, exceptions.AkamaiManagerError) as e:
            self._handle_error(e)

    def _find_network_list_id_by_name(self, name: str) -> str:
        self.logger.info(f"Network List ID not provided. Fetching by name: {name}")
        network_lists = self.api_client.get_networks()
        for network_list in network_lists:
            if network_list.name == name:
                self.logger.info(
                    f"Found Network List ID: {network_list.unique_id} for name: {name}",
                )
                return network_list.unique_id.upper()

        raise exceptions.AkamaiManagerError(
            f"'{name}' {constants.NETWORK_LIST_NOT_FOUND}",
        )

    def _get_network_list_id(self) -> str:
        if self.params.network_list_id:
            self.logger.info(
                f"Using provided Network List ID: {self.params.network_list_id}",
            )
            return self.params.network_list_id.upper()

        if self.params.network_list_name:
            return self._find_network_list_id_by_name(self.params.network_list_name)

        self.logger.error(
            "Unable to determine Network List ID: Neither ID nor "
            "Name was effectively provided.",
        )
        raise exceptions.AkamaiManagerError("Could not determine Network List ID.")

    def _activate_list_via_api(
        self,
        network_list_id: str,
        api_environment: str,
        recipients: list[str] | None,
    ) -> datamodels.NetworkListActivation:
        self.logger.info(
            f"Activating network list ID {network_list_id} in "
            f"{api_environment} environment.",
        )
        return self.api_client.activate_network_list(
            network_list_id=network_list_id,
            environment=api_environment,
            comments=self.params.comment,
            notification_recipients=recipients,
        )

    def _process_successful_activation(
        self,
        activation_result: datamodels.NetworkListActivation,
    ) -> None:
        self.result_value = True
        self.output_message = "Successfully activated the network list in Akamai."

        if activation_result and activation_result.raw_data:
            self.soar_action.result.add_result_json(activation_result.raw_data)
        elif activation_result:
            self.soar_action.result.add_result_json(activation_result.to_json())

    def _handle_error(self, error: Exception) -> None:
        self.result_value = False

        if self._is_authentication_error(error):
            self._handle_authentication_failure(error)
        elif isinstance(error, exceptions.AkamaiManagerError):
            self._handle_specific_akamai_manager_error(error)
        else:
            self._handle_unexpected_error(error)

    def _handle_specific_akamai_manager_error(
        self,
        error: Exception,
    ) -> None:
        if constants.NOT_FOUND_ERROR_MSG in str(error).lower():
            self._handle_network_list_not_found(error)
        else:
            self._handle_other_akamai_manager_error(error)

    def _format_error_message(self, reason: str) -> str:
        network_list_identifier = self.params.network_list_name
        if self.params.network_list_id:
            network_list_identifier = self.params.network_list_id

        if utils.is_reason_indicating_not_found(reason.lower()):
            return f'"{network_list_identifier}" network list wasn\'t found in Akamai.'

        return reason

    def _is_authentication_error(self, error: Exception) -> bool:
        error_message_lower = str(error).lower()
        auth_error_keyword = "invalid authorization"
        return auth_error_keyword in error_message_lower or isinstance(
            error,
            exceptions.AuthenticationError,
        )

    def _handle_authentication_failure(self, error: Exception) -> NoReturn:
        failure_message = str(error)
        self.output_message = self._format_error_message(failure_message)
        self.logger.error(self.output_message)
        raise exceptions.AkamaiManagerError(self.output_message)

    def _handle_network_list_not_found(
        self,
        error: exceptions.AkamaiManagerError,
    ) -> None:
        error_msg = str(error)
        if (
            constants.NOT_FOUND_ERROR_MSG in error_msg
            and self.params.network_list_name in error_msg
        ):
            identifier_used = self.params.network_list_name
        elif self.params.network_list_id:
            identifier_used = self.params.network_list_id
        else:
            identifier_used = "the specified list"

        self.output_message = f"'{identifier_used}' {constants.NETWORK_LIST_NOT_FOUND}"
        self.logger.error(f"{self.output_message} Original error: {error}")
        raise exceptions.AkamaiManagerError(self.output_message)

    def _handle_other_akamai_manager_error(
        self,
        error: exceptions.AkamaiManagerError,
    ) -> None:
        self.output_message = self._format_error_message(str(error))

    def _handle_unexpected_error(self, error: Exception) -> None:
        self.output_message = self._format_error_message(str(error))
        self.logger.exception(error)


def main() -> NoReturn:
    ActivateNetworkList().run()


if __name__ == "__main__":
    main()
