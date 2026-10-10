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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import rename_case

from ..core.ToolsCommon import (
    ExecutionScope,
    get_case_alerts,
    get_execution_scope,
)


@output_handler
def main() -> None:
    """Execute ChangeCaseName action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = "ChangeCaseName"

    output_message = ""
    result_value = "false"
    try:
        change = True
        raw_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert.value)
        execution_scope = get_execution_scope(raw_scope, logger=siemplify.LOGGER)
        info_msg = ""

        if execution_scope.value == ExecutionScope.Alert.value:
            if (
                siemplify.parameters.get("Only If First Alert", "false").lower()
                == "true"
            ):
                alerts = siemplify.case.alerts
                alerts.sort(key=lambda x: (x.detected_time, x.creation_time))
                if len(alerts) > 1 and alerts[0].detected_time == alerts[1].detected_time:
                    siemplify.LOGGER.info(f"First and second alert detected_time is same")
                    if alerts[0].creation_time == alerts[1].creation_time:
                        siemplify.LOGGER.info("creation_time also identical — order may be non-deterministic")
                info_msg = f"\n 1st alert: {alerts[0].identifier} vs this alert: {siemplify.current_alert.identifier}"
                if (
                    siemplify.current_alert.identifier
                    != alerts[0].identifier
                ):
                    change = False

        if change:
            rename_case(
                chronicle_soar=siemplify,
                case_id=siemplify.case_id,
                case_title=siemplify.parameters["New Name"],
            )

            if execution_scope.value == ExecutionScope.Alert.value:
                output_message = (
                    "Case's title changed to: "
                    f"{siemplify.parameters['New Name']}"
                )
            else:
                output_message = (
                    "Case's title changed to: "
                    f"{siemplify.parameters['New Name']} for all alert(s)"
                )
            result_value = "true"
        else:
            output_message = "Case's title not changed, not first alert in the case."
            output_message += info_msg
            result_value = "true"
    except Exception as e:
        output_message = (
            f"Error executing action '{siemplify.script_name}'. Reason: {e}."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
