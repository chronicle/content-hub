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

from typing import Any

from TIPCommon.extraction import extract_action_param

from ..core.base_action import SapErpRfcAction
from ..core.constants import (
    DELETE_USER_SESSION_FUNCTION_ID,
    DELETE_USER_SESSION_SCRIPT_NAME,
    SAP_USERNAME_PARAM,
)


class DeleteUserSessionAction(SapErpRfcAction):
    """Terminate a user's active SAP sessions via TH_DELETE_USER."""

    function_id = DELETE_USER_SESSION_FUNCTION_ID

    def __init__(self, name: str = DELETE_USER_SESSION_SCRIPT_NAME) -> None:
        super().__init__(name)

    def _extract_rfc_parameters(self) -> None:
        self.sap_username: str = (
            extract_action_param(
                siemplify=self.soar_action,
                param_name=SAP_USERNAME_PARAM,
                is_mandatory=True,
                print_value=True,
            )
            or ""
        ).strip()

    def _build_payload(self) -> dict[str, Any]:
        return {
            # TH_DELETE_USER takes CLIENT as an import parameter.
            "username": self.sap_username,
            "client": self.sap_client_number,
        }

    def _get_success_message(self) -> str:
        return f"Successfully deleted user session for {self.sap_username}."

    def _get_failure_prefix(self) -> str:
        return f"Failed to delete user session for {self.sap_username}"


def main() -> None:
    """Run the Delete User Session action."""
    DeleteUserSessionAction().run()


if __name__ == "__main__":
    main()
