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

"""Get Account Password Value action for CyberArk PAM integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param

from ..core.base_action import CyberArkPamAction
from ..core.constants import INTEGRATION_NAME
from ..core.exceptions import CyberArkPamNotFoundError

if TYPE_CHECKING:
    from TIPCommon.types import Entity

SCRIPT_NAME = "Get Account Password Value"


class GetAccountPasswordValue(CyberArkPamAction):
    """Get Account Password Value action class."""

    def __init__(self) -> None:
        """Initialize the GetAccountPasswordValue action."""
        super().__init__(f"{INTEGRATION_NAME} - {SCRIPT_NAME}")
        self.account: str = ""
        self.reason: str = ""
        self.ticketing_system_name: str | None = None
        self.ticket_id: int | None = None
        self.version: int | None = None

    def _extract_action_parameters(self) -> None:
        """Extract action parameters from SOAR."""
        self.account = extract_action_param(
            self.soar_action,
            param_name="Account",
            print_value=True,
            is_mandatory=True,
        )
        self.reason = extract_action_param(
            self.soar_action,
            param_name="Reason",
            print_value=True,
            is_mandatory=True,
        )
        self.ticketing_system_name = extract_action_param(
            self.soar_action,
            param_name="Ticketing System Name",
            print_value=True,
        )
        self.ticket_id = extract_action_param(
            self.soar_action,
            param_name="Ticket ID",
            input_type=int,
            print_value=True,
        )
        self.version = extract_action_param(
            self.soar_action,
            param_name="Version",
            input_type=int,
            print_value=True,
        )

    def _perform_action(self, _: Entity | None = None) -> None:
        """Perform the action logic."""
        try:
            password = self.api_client.get_password(
                account=self.account,
                reason=self.reason,
                ticketing_system_name=self.ticketing_system_name,
                ticket_id=self.ticket_id,
                version=self.version,
            )
            self.output_message = f"Successfully fetched password value for account id {self.account}"
            self.result_value = True
            self.json_results = {"content": password}
        except CyberArkPamNotFoundError:
            self.output_message = (
                f"Password value for account with id {self.account}"
                f"and supplied version {self.version} was not found in the CyberArk PAM"
            )
            self.result_value = False
        except Exception:
            self.logger.exception(f'Error executing action "{SCRIPT_NAME}".')
            raise


def main() -> None:
    """Run the GetAccountPasswordValue action."""
    GetAccountPasswordValue().run()


if __name__ == "__main__":
    main()
