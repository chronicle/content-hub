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
    LOCK_SAP_USER_SCRIPT_NAME,
    SAP_USERNAME_PARAM,
    USER_LOCK_FUNCTION_ID,
)


class LockSapUserAction(SapErpRfcAction):
    """Lock a specified SAP user account via the SAP RFC Gateway."""

    function_id = USER_LOCK_FUNCTION_ID

    def __init__(self, name: str = LOCK_SAP_USER_SCRIPT_NAME) -> None:
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
        return {"username": self.sap_username}

    def _get_success_message(self) -> str:
        return f"Successfully locked user {self.sap_username}."

    def _get_failure_prefix(self) -> str:
        return f"Failed to lock user {self.sap_username}"


def main() -> None:
    """Run the Lock SAP User action."""
    LockSapUserAction().run()


if __name__ == "__main__":
    main()
