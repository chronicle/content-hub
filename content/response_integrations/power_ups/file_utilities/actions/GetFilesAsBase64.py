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
import os

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME = "FileUtilities"
SCRIPT_NAME = "Get Files as Base64"
LOCAL_FOLDER = "downloads"


def get_filenames(filenames):
    file_names = []
    file_parts = []
    for file_part in range(len(filenames)):
        file_name = filenames[file_part]
        if os.path.exists(file_name):
            file_names.append(file_name)
            file_parts = []
        else:
            file_parts.append(file_name)
            for rec_part in range(file_part + 1, len(filenames)):
                file_parts.append(filenames[rec_part])
                file_check = ",".join(file_parts)
                if os.path.exists(file_check):
                    file_names.append(file_check)
                    file_parts = []
                    break
            file_parts = []
    return file_names


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    filenames = list(
        filter(
            None,
            [x.strip() for x in siemplify.parameters.get("File Paths").split(",")],
        ),
    )

    status = EXECUTION_STATE_COMPLETED
    output_message = "Output Message: "
    result_value = "Succeeded"
    json_result = {}
    json_result["filenames"] = []
    json_result["data"] = []
    file_paths = []
    file_names = get_filenames(filenames)
    for file_location in file_names:
        try:
            head_tail = os.path.split(file_location)
            _filename, file_extension = os.path.splitext(file_location)
            file_data = {}
            file_data["path"] = head_tail[0]
            file_data["filename"] = head_tail[1]
            file_data["extension"] = file_extension
            with open(file_location, "rb") as f:
                file_data["base64"] = base64.b64encode(f.read()).decode("utf-8")
            json_result["data"].append(file_data)
            json_result["filenames"].append(file_location)
            file_paths.append(head_tail[1])

        except Exception as e:
            siemplify.LOGGER.exception("General error performing action:\r")
            siemplify.LOGGER.exception(e)
            status = EXECUTION_STATE_FAILED
            result_value = "Failed"
            output_message += "\n unknown failure"
            raise

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.result.add_result_json(json.dumps(json_result))
    siemplify.LOGGER.info(output_message)
    output_message = "Converted Files to Base64: " + ",".join(file_paths)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
