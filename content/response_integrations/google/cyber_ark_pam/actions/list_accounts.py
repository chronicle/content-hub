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

"""List Accounts action for CyberArk PAM integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.base_action import CyberArkPamAction
from ..core.constants import INTEGRATION_NAME

if TYPE_CHECKING:
    from TIPCommon.types import Entity

SCRIPT_NAME = "List Accounts"


class ListAccounts(CyberArkPamAction):
    """List Accounts action class."""

    def __init__(self) -> None:
        """Initialize the ListAccounts action."""
        super().__init__(f"{INTEGRATION_NAME} - {SCRIPT_NAME}")
        self.search_query: str | None = None
        self.search_operator: str | None = None
        self.max_records_to_return: int | None = None
        self.records_offset: int | None = None
        self.filter_query: str | None = None
        self.saved_filter: str | None = None

    def _extract_action_parameters(self) -> None:
        """Extract action parameters from SOAR."""
        self.search_query = extract_action_param(
            self.soar_action, param_name="Search Query", print_value=True
        )
        self.search_operator = extract_action_param(
            self.soar_action, param_name="Search operator", print_value=True
        )
        self.max_records_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Records To Return",
            input_type=int,
            print_value=True,
        )
        self.records_offset = extract_action_param(
            self.soar_action,
            param_name="Records Offset",
            input_type=int,
            print_value=True,
        )
        self.filter_query = extract_action_param(
            self.soar_action, param_name="Filter Query", print_value=True
        )
        self.saved_filter = extract_action_param(
            self.soar_action, param_name="Saved Filter", print_value=True
        )

    def _perform_action(self, _: Entity | None = None) -> None:
        """Perform the action logic.

        Raises:
            ValueError: If parameter validation fails.

        """
        prefix = ""
        if self.filter_query and self.saved_filter:
            prefix = "Both the Filter Query and Saved Filter parameters are provided, Saved Filter takes priority"

        if self.max_records_to_return is not None and self.max_records_to_return <= 0:
            error_msg = (
                f"Invalid value was provided for “Max Records to Return”: "
                f"{self.max_records_to_return}. Positive number should be provided”."
            )
            self.logger.error(error_msg)
            self.output_message = error_msg
            self.result_value = False
            raise ValueError(error_msg)

        if self.records_offset is not None and self.records_offset < 0:
            error_msg = (
                f"Invalid value was provided for “Records Offset to Return”: "
                f"{self.records_offset}. Non negative number should be provided"
            )
            self.logger.error(error_msg)
            self.output_message = error_msg
            self.result_value = False
            raise ValueError(error_msg)

        try:
            accounts = self.api_client.list_accounts(
                search_query=self.search_query,
                search_operator=self.search_operator,
                max_records_to_return=self.max_records_to_return,
                records_offset=self.records_offset,
                filter_query=self.filter_query,
                saved_filter=self.saved_filter,
            )
        except Exception:
            self.logger.exception(f'Error executing action "{SCRIPT_NAME}".')
            raise

        if accounts:
            self.json_results = [account.to_flat() for account in accounts]
            self.soar_action.result.add_data_table(
                "Available PAM Accounts",
                construct_csv([account.to_csv() for account in accounts]),
            )
            self.result_value = True
            log_message = (
                "Successfully found accounts for the provided criteria in CyberArk PAM"
            )
            self.output_message = prefix + log_message if prefix else log_message
        else:
            self.result_value = False
            log_message = (
                "No accounts were found for the provided criteria in CyberArk PAM"
            )
            self.output_message = prefix + log_message if prefix else log_message


def main() -> None:
    """Run the ListAccounts action."""
    ListAccounts().run()


if __name__ == "__main__":
    main()
