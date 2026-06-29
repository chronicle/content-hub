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

from collections.abc import Iterable
from typing import Any, NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.types import SingleJson
from TIPCommon.validation import ParameterValidator
from akamai_integration.core import action_init
from akamai_integration.core import constants
from akamai_integration.core import datamodels
from akamai_integration.core import exceptions


class GetNetworkLists(Action):

    def __init__(self) -> None:
        super().__init__(constants.GET_NETWORK_LISTS_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False
        self.successful_network_lists: list[str] = []
        self.not_found_network_lists: list[str] = []

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
        self.params.include_items = extract_action_param(
            self.soar_action,
            param_name="Include Items",
            input_type=bool,
            default_value=False,
            print_value=True,
        )
        self.params.include_activation_status = extract_action_param(
            self.soar_action,
            param_name="Include Activation Status",
            input_type=bool,
            default_value=False,
            print_value=True,
        )
        self.params.activation_environment = extract_action_param(
            self.soar_action,
            param_name="Activation Environment",
            default_value="Both",
            print_value=True,
        )
        self.params.max_network_lists_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Network Lists To Return",
            input_type=int,
            default_value=constants.DEFAULT_RESULTS_TO_RETURN,
            print_value=True,
            is_mandatory=True,
        )
        self.params.max_network_list_items_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Network List Items To Return",
            input_type=int,
            default_value=constants.DEFAULT_RESULTS_TO_RETURN,
            print_value=True,
            is_mandatory=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        if self.params.network_list_name:
            validator.validate_csv(
                param_name="Network List Name",
                csv_string=self.params.network_list_name,
            )
        if self.params.network_list_id:
            validator.validate_csv(
                param_name="Network List ID",
                csv_string=self.params.network_list_id,
            )
        validator.validate_integer(
            param_name="Max Network Lists To Return",
            value=self.params.max_network_lists_to_return,
            default_value=constants.DEFAULT_RESULTS_TO_RETURN,
        )
        self.params.activation_environment = validator.validate_ddl(
            param_name="Activation Environment",
            value=self.params.activation_environment,
            ddl_values=constants.ENV_LIST,
        )
        validator.validate_range(
            param_name="Max Network Lists To Return",
            value=self.params.max_network_lists_to_return,
            min_limit=constants.MINIMUM_POSITIVE_INTEGER,
            max_limit=constants.DEFAULT_RESULTS_TO_RETURN,
        )
        validator.validate_range(
            param_name="Max Network List Items To Return",
            value=self.params.max_network_list_items_to_return,
            min_limit=constants.MINIMUM_POSITIVE_INTEGER,
            max_limit=constants.DEFAULT_RESULTS_TO_RETURN,
        )

    def _init_api_clients(self) -> None:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _: Any = None) -> None:
        try:
            self._init_api_clients()
            network_lists = self.api_client.get_networks()
            filtered_network_lists = self._filter_network_lists(network_lists)

            user_provided_specific_filters = bool(
                self.params.network_list_name or self.params.network_list_id
            )

            if not filtered_network_lists and user_provided_specific_filters:
                self._handle_no_network_lists_found()
                return

            if self.params.include_activation_status and user_provided_specific_filters:
                self._fetch_activation_statuses(filtered_network_lists)

            limited_network_lists = filtered_network_lists[
                : self.params.max_network_lists_to_return
            ]

            self._process_results(limited_network_lists)

        except (exceptions.AuthenticationError, exceptions.AkamaiManagerError) as e:
            self._handle_error(e)

    def _filter_network_lists(
        self,
        network_lists: Iterable[datamodels.NetworkList],
    ) -> list[datamodels.NetworkList]:
        if not (self.params.network_list_name or self.params.network_list_id):
            return network_lists

        names: list[str] = string_to_multi_value(
            string_value=self.params.network_list_name,
        )

        ids_raw: list[str] = string_to_multi_value(
            string_value=self.params.network_list_id,
        )
        ids: list[str] = [item_id.lower() for item_id in ids_raw]

        return [
            network_list
            for network_list in network_lists
            if (names and network_list.name in names)
            or (ids and network_list.unique_id.lower() in ids)
        ]

    def _fetch_activation_statuses(
        self,
        network_lists: Iterable[datamodels.NetworkList],
    ) -> None:
        for network_list in network_lists:
            if self.params.activation_environment in constants.STAGE_ACTIVATION:
                self._fetch_and_set_activation(
                    network_list,
                    constants.ENV_LIST[2].upper(),
                )
            if self.params.activation_environment in constants.PROD_ACTIVATION:
                self._fetch_and_set_activation(
                    network_list,
                    constants.ENV_LIST[1].upper(),
                )

    def _fetch_and_set_activation(
        self,
        network_list: datamodels.NetworkList,
        environment: str,
    ) -> None:
        try:
            status = self.api_client.get_network_list_activation(
                network_list.unique_id,
                environment,
            )
            setattr(
                network_list,
                f"activation_{environment.lower()}",
                status.to_json() if status else None,
            )
        except exceptions.AkamaiManagerError as e:
            self.logger.error(
                f"Could not retrieve {environment.lower()} activation status "
                f"for network list {network_list.unique_id}: {e}",
            )
            setattr(network_list, f"activation_{environment.lower()}", None)

    def _process_results(self, network_lists: list[datamodels.NetworkList]) -> None:
        if network_lists:
            self.result_value = True
            self.output_message = "Successfully returned network lists from Akamai."
            self.successful_network_lists = [nl.name for nl in network_lists]
            self._add_network_lists_to_result(network_lists)
        else:
            self.result_value = False
            self.output_message = (
                "No network lists were found for the provided criteria in Akamai."
            )

    def _add_network_lists_to_result(
        self,
        network_lists: Iterable[datamodels.NetworkList],
    ) -> None:
        results = [
            self._build_network_list_result(network_list)
            for network_list in network_lists
        ]
        self.soar_action.result.add_result_json(results)

    def _build_network_list_result(
        self,
        network_list: datamodels.NetworkList,
    ) -> SingleJson:
        result = network_list.to_dict()

        if self.params.include_activation_status:
            result.update(self._get_activation_data(network_list))

        if self.params.include_items:
            result["items"] = self._get_item_list(network_list)

        return result

    def _get_activation_data(self, network_list: datamodels.NetworkList) -> SingleJson:
        activation_data = {}
        environments = [env.lower() for env in constants.ACTIVATION_ENVIRONMENTS]
        for env in environments:
            if self.params.activation_environment in [
                constants.ENV_LIST[0],
                env.capitalize(),
            ]:
                activation = getattr(network_list, f"activation_{env}")
                if activation:
                    activation_data[f"Activation_{env.upper()}"] = activation
        return activation_data

    def _get_item_list(self, network_list: datamodels.NetworkList) -> list[str]:
        try:
            item_list_data = self.api_client.get_network_item_list(
                network_list.unique_id,
            )
            all_items = item_list_data.raw_data.get("list", [])
            return all_items[: self.params.max_network_list_items_to_return]
        except exceptions.AkamaiManagerError:
            return []

    def _handle_no_network_lists_found(self) -> None:
        self.output_message = (
            "No network lists were found for the provided criteria in Akamai."
        )
        self.result_value = False

    def _handle_error(self, e: Exception) -> None:
        error_message_lower = str(e).lower()

        self.result_value = False
        self.output_message = f'Error executing action "Get Network Lists". Reason: {e}'
        self.logger.error(f"Error details: {e}")

        if any(char in error_message_lower for char in constants.ERROR_LIST):
            if constants.ERROR_LIST[0] in error_message_lower:
                raise exceptions.AkamaiManagerError(
                    constants.CERTIFICATE_VERIFY_FAILED,
                ) from e

            raise exceptions.AkamaiManagerError(str(e)) from e


def main() -> NoReturn:
    GetNetworkLists().run()


if __name__ == "__main__":
    main()
