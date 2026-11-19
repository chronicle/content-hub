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
from typing import Any, NoReturn, TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator
from ..core import action_init
from ..core import api_manager
from ..core.constants import (
    CLIENT_LIST_TYPE_MAPPING,
    DEFAULT_RESULTS_TO_RETURN,
    GET_CLIENT_LISTS_SCRIPT_NAME,
    LIST_ITEMS,
    MINIMUM_POSITIVE_INTEGER,
)
from ..core.datamodels import ClientList

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class GetClientLists(Action):

    def __init__(self) -> None:
        super().__init__(GET_CLIENT_LISTS_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False
        self.error_output_message: str = (
            f'Error executing action "{GET_CLIENT_LISTS_SCRIPT_NAME}".'
        )
        self.json_results: list[SingleJson] = []

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
        self.params.include_items = extract_action_param(
            self.soar_action,
            param_name="Include Items",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        self.params.include_network_list = extract_action_param(
            self.soar_action,
            param_name="Include Network List",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        self.params.client_list_type = extract_action_param(
            self.soar_action,
            param_name="Type",
            print_value=True,
        )
        self.params.max_client_lists_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Client Lists To Return",
            default_value=DEFAULT_RESULTS_TO_RETURN,
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )

        self.params.max_client_list_item_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Client List Items To Return",
            default_value=DEFAULT_RESULTS_TO_RETURN,
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)

        validator.validate_range(
            param_name="Max Client Lists To Return",
            value=self.params.max_client_lists_to_return,
            min_limit=MINIMUM_POSITIVE_INTEGER,
            max_limit=DEFAULT_RESULTS_TO_RETURN,
        )
        validator.validate_range(
            param_name="Max Client List Items To Return",
            value=self.params.max_client_list_item_to_return,
            min_limit=MINIMUM_POSITIVE_INTEGER,
            max_limit=DEFAULT_RESULTS_TO_RETURN,
        )
        validator.validate_ddl(
            param_name="Type",
            value=self.params.client_list_type,
            ddl_values=list(CLIENT_LIST_TYPE_MAPPING),
        )

    def _perform_action(self, _: Any = None) -> None:
        names_filter, ids_filter = self._get_input_filters()

        fetched_client_lists: list[ClientList] = self._fetch_initial_client_lists(
            names_filter,
            ids_filter,
        )
        filtered_client_lists: list[ClientList] = self._apply_input_filters(
            fetched_client_lists,
            names_filter,
            ids_filter,
        )
        final_json_results: list[SingleJson] = self._prepare_final_results(
            filtered_client_lists,
        )
        self._set_output_message_and_json_results(final_json_results)

    def _get_input_filters(self) -> tuple[set[str], set[str]]:
        names_filter = set(
            string_to_multi_value(
                string_value=self.params.client_list_name,
                only_unique=True,
            )
        )

        ids_filter = set(
            string_to_multi_value(
                string_value=self.params.client_list_id,
                only_unique=True,
            )
        )

        return names_filter, ids_filter

    def _fetch_initial_client_lists(self, names_filter, ids_filter) -> list[ClientList]:
        kwargs = {"client_list_type": self.params.client_list_type}

        if names_filter or ids_filter:
            kwargs["include_items"] = self.params.include_items

        return self.api_client.get_client_lists(**kwargs)

    def _apply_input_filters(
        self,
        client_lists: Iterable[ClientList],
        names_filter: set[str],
        ids_filter: set[str],
    ) -> list[ClientList]:
        if not (names_filter or ids_filter):
            return client_lists

        lower_ids = {id_.lower() for id_ in ids_filter}
        return [
            cl
            for cl in client_lists
            if cl.name in names_filter or cl.list_id.lower() in lower_ids
        ]

    def _prepare_final_results(
        self,
        client_lists: Iterable[ClientList],
    ) -> list[SingleJson]:
        results: list[SingleJson] = []
        seen_ids: set[str] = set()

        for cl in client_lists:
            if cl.list_id in seen_ids:
                continue

            cl_json = cl.to_json()
            if self.params.include_items and isinstance(cl_json.get(LIST_ITEMS), list):
                cl_json[LIST_ITEMS] = cl_json[LIST_ITEMS][
                    : self.params.max_client_list_item_to_return
                ]

            results.append(cl_json)
            seen_ids.add(cl.list_id)

        return results

    def _set_output_message_and_json_results(
        self,
        final_json_results: list[SingleJson],
    ) -> None:
        if final_json_results:
            self.json_results = final_json_results[
                : self.params.max_client_lists_to_return
            ]
            self.output_message = "Successfully returned client lists from Akamai."
            self.result_value = True
        else:
            self.output_message = (
                "No clients lists were found for the provided criteria in Akamai."
            )


def main() -> NoReturn:
    GetClientLists().run()


if __name__ == "__main__":
    main()
