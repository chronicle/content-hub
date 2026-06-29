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

import json
import re
from typing import Any, NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator
from akamai_integration.core import action_init
from akamai_integration.core import constants
from akamai_integration.core import datamodels
from akamai_integration.core import exceptions
from akamai_integration.core import utils


class AddItemsToNetworkLists(Action):

    def __init__(self) -> None:
        super().__init__(constants.ADD_ITEMS_TO_NETWORK_LISTS_SCRIPT_NAME)
        self.network_list_user_provided_identifier: str = ""

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
        self.params.items = extract_action_param(
            self.soar_action,
            param_name="Items",
            print_value=True,
            is_mandatory=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        if not self.params.network_list_name and not self.params.network_list_id:
            raise exceptions.AkamaiManagerError(
                "Provide a value in “Network List Name” or "
                "“Network List ID” parameter.",
            )
        validator.validate_csv(param_name="Items", csv_string=self.params.items)

    def _init_api_clients(self) -> None:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _: Any = None) -> None:
        try:
            self._init_api_clients()
            network_list_id = self._get_network_list_id_from_params()
            items_to_add: list[str] = string_to_multi_value(
                string_value=self.params.items,
            )

            result = self.api_client.add_items_to_network_list(
                network_list_id,
                items_to_add,
            )
            self._process_results(result)

        except (
            exceptions.AuthenticationError,
            exceptions.RequestTakeDownError,
            exceptions.AkamaiManagerError,
        ) as e:
            self._handle_error(e)

    def _get_network_list_id_from_params(self) -> str:
        if self.params.network_list_id:
            self.network_list_user_provided_identifier = self.params.network_list_id
            return self.params.network_list_id.upper()

        network_list_name = self.params.network_list_name
        self.network_list_user_provided_identifier = network_list_name
        self.logger.info(
            f"Network List ID not provided. Fetching by name: {network_list_name}",
        )
        network_list = self._get_network_list_by_name(network_list_name)
        if not network_list:
            raise exceptions.AkamaiManagerError(
                f"'{network_list_name}' {constants.NETWORK_LIST_NOT_FOUND}",
            )
        self.logger.info(
            f"Found Network List ID: {network_list.unique_id} "
            f"for name: {network_list_name}",
        )

        return network_list.unique_id.upper()

    def _get_network_list_by_name(
        self,
        network_list_name: str,
    ) -> datamodels.NetworkList | None:
        return next(
            (
                nl
                for nl in self.api_client.get_networks()
                if nl.name == network_list_name
            ),
            None,
        )

    def _process_results(
        self,
        result: datamodels.AddItemsToNetworkList,
    ) -> None:
        if result:
            self.result_value = True
            self.output_message = (
                "Successfully updated network list "
                f"'{self.network_list_user_provided_identifier}' in Akamai."
            )
            self.soar_action.result.add_result_json(result.to_json())
        else:
            self.result_value = False
            self.output_message = (
                "Failed to update network list "
                f"'{self.network_list_user_provided_identifier}' in Akamai."
            )

    def _handle_error(self, e: Exception) -> None:
        self.result_value = False
        error_message_lower = str(e).lower()
        self._check_and_raise_known_api_errors(e, error_message_lower)
        self._check_and_set_network_list_not_found_error(e)
        self._set_generic_error_output(e)

    def _check_and_raise_known_api_errors(self, e: Any, error_msg_lower: str) -> None:
        if constants.ERROR_LIST[0] in error_msg_lower:
            raise exceptions.AkamaiManagerError(
                constants.CERTIFICATE_VERIFY_FAILED,
            ) from e
        if any(err in error_msg_lower for err in constants.ERROR_LIST):
            raise exceptions.AkamaiManagerError(str(e)) from e

    def _check_and_set_network_list_not_found_error(self, e: Exception) -> None:
        if isinstance(e, exceptions.AkamaiManagerError) and "wasn't found" in str(e):
            self.output_message = (
                f'"{self.network_list_user_provided_identifier}" '
                "network list wasn't found in Akamai."
            )
            raise exceptions.AkamaiManagerError(self.output_message)

    def _set_generic_error_output(self, e: Any) -> None:
        extracted_detail = self._extract_error_info(str(e))
        error_reason_str = str(extracted_detail or e)

        if utils.is_reason_indicating_not_found(error_reason_str):
            error_message = (
                f'"{self.network_list_user_provided_identifier}" network list wasn\'t '
                "found in Akamai."
            )
        else:
            error_message = error_reason_str

        self.logger.error(f"Generic error handler: exception: {e}. ")
        raise exceptions.AkamaiManagerError(error_message) from e

    def _extract_error_info(self, error_msg: str) -> str | None:
        try:
            match = re.search(r"b'(.*)'", error_msg, re.DOTALL)
            if match:
                json_str = match.group(1).replace("\\'", "'")
                return json.loads(json_str).get("detail")
        except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as ex:
            self.logger.exception(f"Failed to extract detail: {ex}")

        return None


def main() -> NoReturn:
    AddItemsToNetworkLists().run()


if __name__ == "__main__":
    main()
