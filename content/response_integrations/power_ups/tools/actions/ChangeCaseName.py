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
from TIPCommon.rest.soar_api import rename_case


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "ChangeCaseName"

    output_message = ""
    result_value = "false"
    try:
        change = True
        siemplify.case.alerts.sort(key=lambda x: x.detected_time)
        if siemplify.parameters.get("Only If First Alert", "false").lower() == "true":
            if siemplify.current_alert.identifier != siemplify.case.alerts[0].identifier:
                change = False
        if change:
            rename_case(
                chronicle_soar=siemplify, case_id=siemplify.case_id, case_title=siemplify.parameters["New Name"]
            )

            output_message = f"Case's title changed to: {siemplify.parameters['New Name']}"
            result_value = "true"
        else:
            output_message = "Case's title not changed, not first alert in the case"
            result_value = "true"
    except Exception as e:
        output_message = "An error occured: " + e
        siemplify.LOGGER.exception(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
