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
import pathlib

from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon import extract_action_param

from ..core.constants import DELETE_FILE_SCRIPT_NAME, FILE_DELETE_STATUS, FILE_NOT_FOUND_STATUS
from ..core.exceptions import AbsolutePathNotFoundError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_FILE_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init ---------------")
    file_path = extract_action_param(
        siemplify, param_name="File Path", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    output_message = "Successfully deleted file."
    status = EXECUTION_STATE_COMPLETED

    json_result = {"filepath": file_path, "status": FILE_DELETE_STATUS}

    try:
        path = pathlib.Path(file_path)

        if not path.is_absolute():
            raise AbsolutePathNotFoundError(
                "Action only works with absolute file paths."
            )

        if path.is_file():
            path.unlink()

        else:
            output_message = "File wasn't found for the provided path."
            json_result.update({"status": FILE_NOT_FOUND_STATUS})

        siemplify.result.add_result_json(json_result)

    except Exception as e:
        siemplify.LOGGER.error(f"Error executing action “Delete File”. Reason: {e}")
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action “Delete File”. Reason: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
