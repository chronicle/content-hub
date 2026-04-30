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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.FileUtilitiesManager import EntityFileManager

# Example Consts:
INTEGRATION_NAME = "FileUtilities"

SCRIPT_NAME = "Add Entity to File"
FILE_PATH = "/tmp/"
timeout = 200


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

    filename = siemplify.extract_action_param(
        param_name="Filename",
        is_mandatory=False,
        print_value=True,
    )

    output_message = ""
    result_value = True
    filepath = FILE_PATH + filename
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        # Lock the file from other actions that may use it. if file
        with EntityFileManager(filepath, timeout) as efm:
            for entity in siemplify.target_entities:
                if entity.identifier not in efm.entities:
                    siemplify.LOGGER.info(f"Adding entity: {entity.identifier}")
                    efm.add_entity(entity.identifier)
                    output_message += f"Added Entity: {entity.identifier}\n"
                else:
                    siemplify.LOGGER.info(
                        f"Entity is already in file: {entity.identifier}",
                    )
                    output_message += f"Entity is already in file: {entity.identifier}\n"
                    result_value = False

    except Exception as e:
        siemplify.LOGGER.exception("General error performing action %s", SCRIPT_NAME)
        siemplify.LOGGER.exception(e)
        raise

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
