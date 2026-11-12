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

from ..core.base_action import SapErpRfcAction
from ..core.constants import (
    ACTIVATE_AUDIT_LOG_FUNCTION_ID,
    ACTIVATE_AUDIT_LOG_SCRIPT_NAME,
)


class ActivateAuditLogAction(SapErpRfcAction):
    """Activate the SAP Security Audit Log via the SAP RFC Gateway."""

    function_id = ACTIVATE_AUDIT_LOG_FUNCTION_ID
    success_message = "Successfully activated SAP audit log."
    failure_prefix = "Failed to activate audit log"

    def __init__(self, name: str = ACTIVATE_AUDIT_LOG_SCRIPT_NAME) -> None:
        super().__init__(name)


def main() -> None:
    """Run the Activate Audit Log action."""
    ActivateAuditLogAction().run()


if __name__ == "__main__":
    main()
