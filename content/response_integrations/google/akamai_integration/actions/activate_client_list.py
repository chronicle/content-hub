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

from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator
from akamai_integration.core import action_init
from akamai_integration.core import constants
from akamai_integration.core import exceptions
from akamai_integration.core import utils

if TYPE_CHECKING:
    from typing import Any, Never, NoReturn
    from akamai_integration.core import datamodels


class ActivateClientList(Action):

    def __init__(self) -> None:
        super().__init__(constants.ACTIVATE_CLIENT_LIST_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False

    def _extract_action_parameters(self) -> None:
        self.params.client_list_name = extract_action_param(
            self.soar_action,
            param_name="Client List Name",
            print_value=True,
        )
        self.params.client_list_id = extract_action_param(
            self.soar_action,
            param_name="Client List ID",
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
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        if not (self.params.client_list_name or self.params.client_list_id):
            raise exceptions.AkamaiManagerError(
                'Provide a value in "Client List Name" or '
                '"Client List ID" parameter.',
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

    def _perform_action(self, _: Never) -> None:
        try:
            client_list_id: str = self._get_client_list_id()

            recipients: list[str] | None = string_to_multi_value(
                string_value=self.params.notification_recipients,
            )

            api_environment: str | None = constants.API_ENVIRONMENTS.get(
                self.params.environment
            )

            activation_result: datamodels.ClientActivation = (
                self._activate_list_via_api(
                    client_list_id,
                    api_environment,
                    recipients,
                )
            )

            self._process_successful_activation(activation_result)

        except (exceptions.AuthenticationError, exceptions.AkamaiManagerError) as e:
            self._handle_error(e)

    def _find_client_list_id_by_name(
        self,
        name: str,
    ) -> str:
        self.logger.info(f"Client List ID not provided. Fetching by name: {name}")
        client_lists: list[datamodels.ClientList] = self.api_client.get_client_lists()
        for client_list in client_lists:
            if client_list.name == name:
                self.logger.info(
                    f"Found Client List ID: {client_list.list_id} for name: {name}",
                )
                return client_list.list_id.upper()

        raise exceptions.AkamaiManagerError(
            f"'{name}' {constants.CLIENT_LIST_NOT_FOUND}",
        )

    def _get_client_list_id(self) -> str:
        if self.params.client_list_id:
            self.logger.info(
                f"Using provided Client List ID: {self.params.client_list_id}",
            )
            return self.params.client_list_id.upper()

        if self.params.client_list_name:
            return self._find_client_list_id_by_name(self.params.client_list_name)

        self.logger.error(
            "Unable to determine Client List ID: Neither ID nor "
            "Name was effectively provided.",
        )
        raise exceptions.AkamaiManagerError("Could not determine Client List ID.")

    def _activate_list_via_api(
        self,
        client_list_id: str,
        api_environment: str,
        recipients: list[str] | None,
    ) -> datamodels.ClientActivation:
        self.logger.info(
            f"Activating client list ID {client_list_id} in "
            f"{api_environment} environment.",
        )
        return self.api_client.activate_client_list(
            client_list_id=client_list_id,
            environment=api_environment,
            comments=self.params.comment,
            notification_recipients=recipients,
        )

    def _process_successful_activation(
        self,
        activation_result: datamodels.ClientActivation,
    ) -> None:
        self.result_value = True
        self.output_message = "Successfully activated the client list in Akamai."

        if not activation_result:
            return

        if activation_result.raw_data:
            self.soar_action.result.add_result_json(activation_result.raw_data)
            return

        self.soar_action.result.add_result_json(activation_result.to_json())

    def _handle_error(self, error: Exception) -> None:
        self.result_value = False

        if self._is_authentication_error(error):
            self._handle_authentication_failure(error)

        if isinstance(error, exceptions.AkamaiManagerError):
            self._handle_specific_akamai_manager_error(error)
            return

        self._handle_unexpected_error(error)

    def _handle_specific_akamai_manager_error(
        self,
        error: Exception,
    ) -> None:
        if constants.NOT_FOUND_ERROR_MSG in str(error).lower():
            self._handle_client_list_not_found(error)
            return

        self._handle_other_akamai_manager_error(error)

    def _format_error_message(self, reason: str) -> str:
        client_list_identifier: str = self.params.client_list_name
        if self.params.client_list_id:
            client_list_identifier = self.params.client_list_id

        if utils.is_reason_indicating_not_found(reason.lower()):
            return f'"{client_list_identifier}" client list wasn\'t found in Akamai.'

        return reason

    def _is_authentication_error(self, error: Exception) -> bool:
        error_message_lower: str = str(error).lower()
        auth_error_keyword: str = "invalid authorization"
        return auth_error_keyword in error_message_lower or isinstance(
            error,
            exceptions.AuthenticationError,
        )

    def _handle_authentication_failure(self, error: Exception) -> NoReturn:
        failure_message: str = str(error)
        self.output_message: str = self._format_error_message(failure_message)
        self.logger.error(self.output_message)
        raise exceptions.AkamaiManagerError(self.output_message)

    def _handle_client_list_not_found(
        self,
        error: exceptions.AkamaiManagerError,
    ) -> None:
        error_msg: str = str(error)
        identifier_used: str
        if (
            constants.NOT_FOUND_ERROR_MSG in error_msg
            and self.params.client_list_name in error_msg
        ):
            identifier_used = self.params.client_list_name
        elif self.params.client_list_id:
            identifier_used = self.params.client_list_id
        else:
            identifier_used = "the specified list"

        self.output_message: str = (
            f"'{identifier_used}' {constants.CLIENT_LIST_NOT_FOUND}"
        )
        self.logger.error(f"{self.output_message} Original error: {error}")
        raise exceptions.AkamaiManagerError(self.output_message)

    def _handle_other_akamai_manager_error(
        self,
        error: exceptions.AkamaiManagerError,
    ) -> None:
        self.output_message: str = self._format_error_message(str(error))

    def _handle_unexpected_error(self, error: Exception) -> None:
        self.output_message: str = self._format_error_message(str(error))
        self.logger.exception(error)


def main() -> NoReturn:
    ActivateClientList().run()


if __name__ == "__main__":
    main()
