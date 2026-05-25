# Copyright 2025 Google LLC
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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ToolsCommon import ExecutionScope

SCRIPT_NAME: str = "FindFirstAlert"


@output_handler
def main():
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    execution_scope: ExecutionScope = getattr(
        siemplify, "execution_scope", ExecutionScope.Alert
    )
    
    alerts = getattr(siemplify.case, "open_alerts", siemplify.case.alerts)
    alerts.sort(key=lambda x: x.creation_time)
    first_alert: Any = alerts[0]

    if execution_scope.value == ExecutionScope.Alert.value:
        output_message: str = (
            f"First alert is: {first_alert.identifier} "
            f"Created at: {first_alert.creation_time}\n"
        )
        output_message += (
            f"This alert is: {siemplify.current_alert.identifier}. "
            f"Created at: {siemplify.current_alert.creation_time}\n\n"
        )
        if siemplify.current_alert.identifier == first_alert.identifier:
            output_message += "This is the first alert."
            siemplify.end(output_message, siemplify.current_alert.identifier)
        else:
            output_message += "This is NOT the first alert."
            siemplify.end(output_message, "false")
        
    else:
        output_message: str = (
            f"First alert of the case is: {first_alert.identifier} "
            f"Created at: {first_alert.creation_time}\n"
        )
        siemplify.end(output_message, first_alert.identifier)


if __name__ == "__main__":
    main()
