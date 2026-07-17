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


"""Get Account Password Versions action for CyberArk PAM integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value

from ..core.base_action import CyberArkPamAction
from ..core.constants import INTEGRATION_NAME
from ..core.exceptions import (
    CyberArkPamAccountNotManagedError,
    CyberArkPamNotFoundError,
)

if TYPE_CHECKING:
    from TIPCommon.types import Entity

SCRIPT_NAME = "Get Account Password Versions"


class GetAccountPasswordVersions(CyberArkPamAction):
    """Get Account Password Versions action class."""

    def __init__(self) -> None:
        """Initialize the GetAccountPasswordVersions action."""
        super().__init__(f"{INTEGRATION_NAME} - {SCRIPT_NAME}")
        self.accounts: list[str] = []
        self.successful_accounts: dict[str, Any] = {}
        self.failed_accounts: dict[str, str] = {}

    def _extract_action_parameters(self) -> None:
        """Extract action parameters from SOAR."""
        account_str = extract_action_param(
            self.soar_action,
            param_name="Account ID",
            print_value=True,
            is_mandatory=True,
        )
        self.accounts = string_to_multi_value(account_str)

    def _perform_action(self, _: Entity | None = None) -> None:
        """Perform the action logic."""
        for account in self.accounts:
            try:
                versions = self.api_client.get_secret_versions(account=account)
                self.successful_accounts[account] = versions
            except CyberArkPamNotFoundError as e:
                self.logger.exception(f"Account with id {account} was not found in CyberArk PAM.")
                self.failed_accounts[account] = str(e)
            except CyberArkPamAccountNotManagedError as e:
                self.logger.exception(f"Account with id {account} is not managed by the CPM.")
                self.failed_accounts[account] = str(e)
            except Exception as e:
                self.logger.exception(f"Error executing action on account {account}.")
                self.failed_accounts[account] = str(e)

        self._finalize_output()

    def _finalize_output(self) -> None:
        """Finalize the action output message and result value."""
        output_parts: list[str] = []
        self.result_value = True

        if self.successful_accounts:
            output_parts.append(
                "Successfully retrieved secret versions in CyberArk PAM for "
                f"the following accounts: {', '.join(self.successful_accounts.keys())}"
            )

        if self.failed_accounts:
            self.result_value = False
            if self.successful_accounts:
                output_parts.append(
                    "Action wasn't able to retrieve secret versions in CyberArk PAM for "
                    f"the following accounts: {', '.join(self.failed_accounts.keys())}. "
                    "Please check JSON Result for more information."
                )
            else:
                output_parts.append(
                    "None of the provided accounts were retrieved for secret versions. "
                    "Please check JSON Result for more information."
                )

        self.output_message = "\n".join(output_parts)

        self.json_results = {
            "successful_accounts": [
                {"account_id": acc, "versions": versions} for acc, versions in self.successful_accounts.items()
            ],
            "failed_accounts": [{"account_id": acc, "error": reason} for acc, reason in self.failed_accounts.items()],
        }


def main() -> None:
    """Run the GetAccountPasswordVersions action."""
    GetAccountPasswordVersions().run()


if __name__ == "__main__":
    main()
