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
from typing import TYPE_CHECKING, Any, NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from ..core import action_init
from ..core import api_manager
from ..core import exceptions
from ..core import utils
from ..core.constants import (
    ADD_ITEMS_TO_CLIENT_LISTS_SCRIPT_NAME,
)
from ..core.datamodels import ClientList, ClientListItemDetails

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class AddItemsToClientList(Action):

    def __init__(self) -> None:
        super().__init__(ADD_ITEMS_TO_CLIENT_LISTS_SCRIPT_NAME)
        self.error_output_message: str = (
            f'Error executing action "{ADD_ITEMS_TO_CLIENT_LISTS_SCRIPT_NAME}".'
        )
        self.json_results: list = []
        self.target_client_list: str = ""
        self.all_client_lists: list[ClientList] = []

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
        self.params.item_value = extract_action_param(
            self.soar_action,
            param_name="Item Value",
            is_mandatory=True,
            print_value=True,
        )
        self.params.item_description = extract_action_param(
            self.soar_action,
            param_name="Item Description",
            print_value=True,
        )
        self.params.item_expiration_date = extract_action_param(
            self.soar_action,
            param_name="Item Expiration Date",
            print_value=True,
        )
        self.params.item_tags = extract_action_param(
            self.soar_action,
            param_name="Item Tags",
            print_value=True,
        )
        self.params.item_tags = string_to_multi_value(
            string_value=self.params.item_tags,
            only_unique=True,
        )
        self.params.item_value = string_to_multi_value(
            string_value=self.params.item_value,
            only_unique=True,
        )

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _validate_params(self) -> None:
        if not self.params.client_list_name and not self.params.client_list_id:
            raise exceptions.AkamaiManagerError(
                'provide a value in "Client List Name" or "Client List ID" parameter.',
            )

        self.target_client_list: str = self._get_target_client_list_for_update()

        try:
            self.all_client_lists: list[ClientList] = self.api_client.get_client_lists()
        except Exception as e:
            raise exceptions.AkamaiManagerError(
                "Could not retrieve the client lists from Akamai for validation. "
                f"Error: {e}",
            ) from e

        if self.params.item_expiration_date:
            utils.validate_iso8601_date_format(self.params.item_expiration_date)

    def _perform_action(self, _: Any = None) -> None:
        self._resolve_client_ids()
        results: list[SingleJson] = self._process_items()
        self._finalize_results(results)

    def _add_item_to_list(self, item: str) -> SingleJson:
        item_payload: ClientListItemDetails = self._build_item_payload(item)
        added_items: list[Any] = self.api_client.add_items_to_client_list(
            list_id=self.target_client_list,
            item_details=item_payload,
        )
        added_item_details: SingleJson = added_items[0].raw_data
        added_item_details["status"] = "added"
        return added_item_details

    def _handle_item_addition_error(
        self,
        item: str,
        error: Exception,
    ) -> dict[str, str]:
        error_reason: str = self._parse_error_reason(error)
        is_existing_item_error: bool = (
            "already exist" in error_reason.lower()
            or "is on the list" in error_reason.lower()
        )

        if is_existing_item_error:
            return {"value": item, "status": "duplicated"}

        return {"value": item, "status": "failed", "error": error_reason}

    def _process_single_item(self, item: str) -> SingleJson:
        try:
            return self._add_item_to_list(item)
        except (
            exceptions.AuthenticationError,
            exceptions.AkamaiManagerError,
        ) as e:
            return self._handle_item_addition_error(item, e)

    def _process_items(self) -> list[SingleJson]:
        results: list[SingleJson] = [
            self._process_single_item(item) for item in self.params.item_value
        ]
        return results

    def _finalize_results(self, results: list[SingleJson]) -> None:
        self.json_results: list[SingleJson] = results

        if any(item.get("status") == "failed" for item in results):
            self.output_message: str = (
                "One or more items were not added. See JSON results for details."
            )
        else:
            self.output_message: str = "Successfully updated client list in Akamai."

        self.result_value: bool = any(
            item.get("status") in ["added", "duplicated"] for item in results
        )

    def _build_item_payload(self, item_value: str) -> ClientListItemDetails:
        return ClientListItemDetails(
            values=[item_value],
            tags=self.params.item_tags,
            description=self.params.item_description,
            expiration_date=self.params.item_expiration_date,
        )

    def _parse_error_reason(self, error: Exception) -> str:
        error_details: str = str(error)
        try:
            error_json: SingleJson = json.loads(error_details)
            reason: str = error_json.get("title", error_details)
            if "detail" in error_json:
                reason = f"{reason}: {error_json.get('detail')}"
            return reason
        except json.JSONDecodeError:
            return error_details

    def _get_target_client_list_for_update(self) -> str:
        if self.params.client_list_id is not None:
            return self.params.client_list_id

        return self.params.client_list_name

    def _resolve_client_ids(self) -> None:
        for client_list in self.all_client_lists:
            if self._is_matching_client_list(self.target_client_list, client_list):
                self.target_client_list: str = client_list.list_id
                return

        raise exceptions.AkamaiManagerError(
            f'"{self.target_client_list}" client list wasn\'t found in Akamai.',
        )

    def _is_matching_client_list(
        self,
        target_identifier: str,
        client_list: ClientList,
    ) -> bool:
        target_lower: str = target_identifier.lower()
        return (
            target_lower == client_list.name.lower()
            or target_lower == client_list.list_id.lower()
        )


def main() -> NoReturn:
    AddItemsToClientList().run()


if __name__ == "__main__":
    main()
