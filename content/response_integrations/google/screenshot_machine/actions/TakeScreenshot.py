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
import base64
from typing import NoReturn

import requests

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    convert_unixtime_to_datetime,
    output_handler,
    unix_now,
)

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from screenshot_machine.core.ScreenshotMachineManager import (
    ScreenshotMachineInvalidAPIKeyManagerError,
    ScreenshotMachineLimitManagerError,
    ScreenshotMachineManager,
)

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)


SCRIPT_NAME = "ScreenshotMachine - TakeScreenshot"
INTEGRATION_NAME = "ScreenshotMachine"
DEFAULT_DELAY = 2000

SUPPORTED_ENTITIES = [EntityTypes.URL, EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main() -> NoReturn:
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Key", input_type=str
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        default_value=False,
        input_type=bool,
    )

    image_format = extract_action_param(
        siemplify, param_name="Image Format", input_type=str
    )

    delay = (
        int(siemplify.parameters.get("Delay", DEFAULT_DELAY))
        if siemplify.parameters.get("Delay")
        else DEFAULT_DELAY
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = {}

    try:
        screenshot_machine_manager = ScreenshotMachineManager(api_key, use_ssl=use_ssl)
        status = EXECUTION_STATE_COMPLETED
        output_message = ""
        result_value = False
        failed_entities = []
        successful_entities = []

        for entity in siemplify.target_entities:
            current_entity_identifier = entity.additional_properties.get(
                "OriginalIdentifier", entity.identifier
            )
            siemplify.LOGGER.info(
                f"Started processing entity: {current_entity_identifier}"
            )
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            if entity.entity_type in SUPPORTED_ENTITIES:
                try:
                    screenshot_content = screenshot_machine_manager.get_screenshot(
                        current_entity_identifier,
                        image_format=image_format,
                        delay=delay,
                    )

                    # Attach screenshot
                    siemplify.result.add_entity_attachment(
                        current_entity_identifier,
                        f"Screenshot.{image_format}",
                        base64.b64encode(screenshot_content).decode(),
                    )

                    json_results[current_entity_identifier] = base64.b64encode(
                        screenshot_content
                    )

                    successful_entities.append(current_entity_identifier)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {current_entity_identifier}"
                    )

                except (
                    ScreenshotMachineInvalidAPIKeyManagerError,
                    requests.exceptions.ConnectionError,
                ):
                    raise

                except ScreenshotMachineLimitManagerError:
                    status = EXECUTION_STATE_FAILED
                    result_value = False
                    output_message = (
                        "You have reached the maximum allowed number of API requests."
                    )
                    siemplify.end(output_message, result_value, status)

                except Exception as e:
                    failed_entities.append(current_entity_identifier)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {current_entity_identifier}"
                    )
                    siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += "\n Successfully returned screenshot for the following entities:\n   {}".format(
                "\n   ".join(successful_entities)
            )
            result_value = True

        if failed_entities:
            output_message += "\n Action wasn't able to return screenshot for the following entities:\n   {}".format(
                "\n   ".join(failed_entities)
            )

        if not failed_entities and not successful_entities:
            output_message = (
                "Action wasn't able to return screenshot for the provided entities."
            )

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"An error occurred while running action: {e}"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
