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

import base64
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import import_simulator_custom_case


# The output_handler decorator manages output for Siemplify actions.
@output_handler
def main():
    try:
        siemplify = SiemplifyAction(get_source_file=True)

    except TypeError:
        siemplify = SiemplifyAction()

    push_to_simulated = siemplify.extract_action_param(
        "Push to Simulated Cases",
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    save_to_case_wall = siemplify.extract_action_param(
        "Save JSON as Case Wall File",
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    override_name = siemplify.extract_action_param(
        "Override Alert Name",
        default_value="",
        print_value=True,
    )
    full_path_name = siemplify.extract_action_param(
        "Full path name",
        default_value="",
        print_value=True,
    )

    output_message = "Action result: "

    # Check if the 'SourceFileContent' property exists in the alert data before trying to load it.
    if "SourceFileContent" in siemplify.current_alert.entities[0].additional_properties:
        # Load the alert data from the 'SourceFileContent' property.
        case_data = json.loads(
            siemplify.current_alert.entities[0].additional_properties["SourceFileContent"],
        )
    else:
        siemplify.LOGGER.error("Alert data is missing 'SourceFileContent' property")
        return

    # Modify the 'Event Name' fields in the alert data.
    for i, event in enumerate(case_data["Events"]):
        if "DeviceEventClassId" in case_data["Events"][i]["_fields"]:
            case_data["Events"][i]["_rawDataFields"]["DeviceEventClassId"] = case_data["Events"][i]["_fields"][
                "DeviceEventClassId"
            ]
            case_data["Events"][i]["_rawDataFields"]["Name"] = case_data["Events"][i]["_fields"]["DeviceEventClassId"]
        if "deviceEventClassId" in case_data["Events"][i]["_fields"]:
            case_data["Events"][i]["_rawDataFields"]["DeviceEventClassId"] = case_data["Events"][i]["_fields"][
                "deviceEventClassId"
            ]
            case_data["Events"][i]["_rawDataFields"]["Name"] = case_data["Events"][i]["_fields"]["deviceEventClassId"]

    # Optionally modify the 'Name' field in the alert data.
    if full_path_name:
        case_data["Name"] = case_data["SourceSystemName"] + "_" + case_data["DeviceProduct"] + "_" + case_data["Name"]
    if override_name:
        case_data["Name"] = override_name

    # Prepare the data to be pushed or saved.
    my_json = {"cases": [case_data]}

    # Push the data to the simulator or save it as a JSON file, depending on the parameters.
    if push_to_simulated:
        import_simulator_custom_case(siemplify, my_json)
        output_message += " Pushed to Simulated "

    if save_to_case_wall:
        s = json.dumps(my_json)
        t = base64.b64encode(s.encode("utf-8")).decode("ascii")
        siemplify.result.add_attachment(
            title="<<file in here>>",
            filename=case_data["Name"] + ".case",
            file_contents=t,
        )
        output_message += " Saved to Casewall "
    # The action is complete.
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    # Add the JSON data to the action result and end the action.
    siemplify.result.add_result_json(my_json)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
