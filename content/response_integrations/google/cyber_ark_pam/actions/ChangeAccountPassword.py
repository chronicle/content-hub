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

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value

from ..core.base_action import CyberArkPamAction
from ..core.constants import INTEGRATION_NAME
from ..core.CyberArkPamManager import CyberArkPamNotFoundError

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import Entity

SCRIPT_NAME = "Change Account Password"


class ChangeAccountPassword(CyberArkPamAction):
    def __init__(self) -> None:
        super().__init__(f"{INTEGRATION_NAME} - {SCRIPT_NAME}")
        self.successful_accounts: list[str] = []
        self.failed_accounts: dict[str, str] = {}

    def _extract_action_parameters(self) -> None:
        account_str = extract_action_param(
            self.soar_action,
            param_name="Account ID",
            print_value=True,
            is_mandatory=True,
        )
        self.params.accounts = string_to_multi_value(account_str)

    def _perform_action(self, _: Entity | None = None) -> None:
        for account in self.params.accounts:
            try:
                self.api_client.change_password(account=account)
                self.successful_accounts.append(account)
            except CyberArkPamNotFoundError as e:
                self.logger.exception(f"Account with id {account} was not found in CyberArk PAM.")
                self.logger.exception(e)
                self.failed_accounts[account] = "Account was not found in CyberArk PAM."
            except Exception as e:
                self.logger.exception(f"Error executing action on account {account}. Reason: {e}")
                self.logger.exception(e)
                self.failed_accounts[account] = str(e)

        self._finalize_output()

    def _finalize_output(self) -> None:
        output_parts: list[str] = []
        if self.successful_accounts:
            output_parts.append(
                "Successfully marked the following accounts for an immediate credentials change by the CPM to a "
                f"new random value: {', '.join(self.successful_accounts)}"
            )

        if self.failed_accounts:
            failed_details = [f"{acc} (Reason: {reason})" for acc, reason in self.failed_accounts.items()]
            output_parts.append(
                "Action wasn't able to mark the following accounts for password change in CyberArk PAM: "
                f"{', '.join(failed_details)}"
            )

        self.output_message = "\n".join(output_parts)
        self.result_value = True

        if self.failed_accounts:
            self.result_value = False

        if not self.successful_accounts:
            self.result_value = False
            failed_details = [f"- {acc}: {reason}" for acc, reason in self.failed_accounts.items()]
            reasons_str = "\n".join(failed_details)
            self.output_message = "None of the provided accounts were marked for password change."
            if reasons_str:
                self.output_message += f"\nReasons:\n{reasons_str}"


def main() -> NoReturn:
    """Run the ChangeAccountPassword action."""
    ChangeAccountPassword().run()


if __name__ == "__main__":
    main()
