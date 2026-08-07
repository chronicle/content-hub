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
from TIPCommon.validation import ParameterValidator
from ..core import action_init
from ..core import constants
from ..core import exceptions
from ..core import utils


class RemoveItemsFromNetworkLists(Action):

    def __init__(self) -> None:
        super().__init__(constants.REMOVE_ITEMS_FROM_NETWORK_LISTS_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False
        self.json_result: list[dict[str, Any]] = []

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

        if not self.params.network_list_name and not self.params.network_list_id:
            raise exceptions.AkamaiManagerError(
                'provide a value in "Network List Name" or '
                '"Network List ID" parameter.',
            )

    def _init_api_clients(self) -> None:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _: Any = None) -> None:
        try:
            self._init_api_clients()
            network_list_id: str = self._get_network_list_id()
            items_to_remove: list[str] = self._parse_items_to_remove()

            if not items_to_remove:
                self.output_message = (
                    "No valid items provided for removal. Please provide a "
                    "comma-separated list of items."
                )
                self.result_value = False
                return

            successful_removals, failed_removals = self._process_item_removals(
                network_list_id,
                items_to_remove,
            )

            self._set_action_outcome(successful_removals, failed_removals)

            if self.json_result:
                self.soar_action.result.add_result_json(self.json_result)

        except (exceptions.AuthenticationError, exceptions.AkamaiManagerError) as e:
            self._handle_error(e)

    def _get_network_list_id(self) -> str:
        if self.params.network_list_id:
            return self.params.network_list_id.upper()

        if self.params.network_list_name:
            self.logger.info(
                f"Network List ID not provided. Fetching by name: "
                f"{self.params.network_list_name}",
            )
            network_lists = self.api_client.get_networks()
            for network_list in network_lists:
                if network_list.name == self.params.network_list_name:
                    self.logger.info(
                        f"Found Network List ID: {network_list.unique_id} for name: "
                        f"{self.params.network_list_name}",
                    )
                    return network_list.unique_id.upper()

            raise exceptions.AkamaiManagerError(
                f"Network list with name '{self.params.network_list_name}' "
                "wasn't found in Akamai.",
            )

        raise exceptions.AkamaiManagerError(
            "Unable to determine Network List ID: Neither ID nor Name provided.",
        )

    def _parse_items_to_remove(self) -> list[str]:
        return [item.strip() for item in self.params.items.split(",") if item.strip()]

    def _process_item_removals(
        self,
        network_list_id: str,
        items_to_remove: list[str],
    ) -> tuple[list[str], list[str]]:
        successful_removals: list[str] = []
        failed_removals: list[str] = []

        self.logger.info(
            f"Attempting to remove items: {', '.join(items_to_remove)} "
            f"from network list ID: {network_list_id}",
        )
        for item in items_to_remove:
            if self._remove_single_item_from_list(network_list_id, item):
                successful_removals.append(item)
            else:
                failed_removals.append(item)
        return successful_removals, failed_removals

    def _remove_single_item_from_list(self, network_list_id: str, item: str) -> bool:
        try:
            self.logger.info(
                f"Attempting to remove item: {item} from list {network_list_id}",
            )
            remove_result = self.api_client.remove_item_from_network_list(
                network_list_id=network_list_id,
                item=item,
            )
            self.json_result.append(remove_result.to_json())
            self.logger.info(f"Successfully removed item: {item}")
            return True
        except (
            exceptions.AuthenticationError,
            exceptions.AkamaiManagerError,
        ) as e_item:
            if utils.is_reason_indicating_not_found(e_item):
                self.output_message = self._format_network_list_not_found_message()
                raise exceptions.AkamaiManagerError(self.output_message)
            return False

    def _set_action_outcome(
        self,
        successful_removals: list[str],
        failed_removals: list[str],
    ) -> None:
        if successful_removals:
            self.result_value = True
            self.output_message = "Successfully updated network list in Akamai."
            if failed_removals:
                partially_failed_message = (
                    f"Successfully removed: {', '.join(successful_removals)}. "
                    f"Failed to remove: {', '.join(failed_removals)}."
                )
                self.logger.info(partially_failed_message)

        elif failed_removals:
            self.result_value = False
            self.output_message = (
                "None of the provided items were found in the network list in Akamai."
            )
            self.logger.error(
                f"{self.output_message} Items not found: {', '.join(failed_removals)}.",
            )
            raise exceptions.AkamaiManagerError(self.output_message)
        else:
            self.result_value = False
            self.output_message = "No items were provided or found to process."
            self.logger.info(self.output_message)

    def _handle_error(self, e: Exception) -> None:
        error_message_lower = str(e).lower()
        self.result_value = False

        if any(
            err_pattern in error_message_lower for err_pattern in constants.ERROR_LIST
        ):
            if constants.ERROR_LIST[0] in error_message_lower:
                self.output_message = constants.CERTIFICATE_VERIFY_FAILED
                self.logger.error(self.output_message)
                raise exceptions.AkamaiManagerError(self.output_message) from e

            self.output_message = str(e)
            self.logger.error(self.output_message)
            raise exceptions.AkamaiManagerError(self.output_message) from e

        if (
            isinstance(e, exceptions.AkamaiManagerError)
            and "wasn't found in akamai" in error_message_lower
        ):
            self.output_message = self._format_network_list_not_found_message()
            self.logger.error(self.output_message)
            raise exceptions.AkamaiManagerError(self.output_message)

        self.output_message = str(e)
        self.logger.error(
            "Error details for action "
            f"{constants.REMOVE_ITEMS_FROM_NETWORK_LISTS_SCRIPT_NAME}: {e}",
        )
        self.logger.exception(e)

    def _format_network_list_not_found_message(self) -> str:
        if not self.params.network_list_id:
            chosen_identifier = self.params.network_list_name
        else:
            chosen_identifier = self.params.network_list_id

        return f'"{chosen_identifier}" network list wasn\'t found in Akamai.'


def main() -> NoReturn:
    RemoveItemsFromNetworkLists().run()


if __name__ == "__main__":
    main()
