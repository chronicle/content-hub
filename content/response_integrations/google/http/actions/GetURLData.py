from __future__ import annotations
import urllib.parse

import requests
from TIPCommon import extract_action_param

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_TIMEDOUT,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_COMPLETED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
)

SCRIPT_NAME = "Get URL Data"
INTEGRATION_NAME = "HTTP"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"

    siemplify.LOGGER.info("================= Main - Param Init =================")

    username = extract_action_param(
        siemplify,
        param_name="Username",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    password = extract_action_param(
        siemplify,
        param_name="Password",
        is_mandatory=False,
        input_type=str,
        print_value=False,
    )

    ssl_verify = extract_action_param(
        siemplify,
        param_name="SSL Verification",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = "false"
    failed_entities = []
    successful_entities = []
    json_results = {}

    try:
        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            if entity.entity_type == EntityTypes.URL:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                try:
                    if not urllib.parse.urlparse(entity.identifier).scheme:
                        siemplify.LOGGER.info(
                            "No schema in the URL. Prepending http://"
                        )
                        url = "http://" + entity.identifier

                    else:
                        url = entity.identifier

                    siemplify.LOGGER.info(f"Sending GET request to {url}")

                    if username and password:
                        try:
                            response = requests.get(
                                url, auth=(username, password), verify=ssl_verify
                            )
                        except requests.exceptions.InvalidSchema:
                            siemplify.LOGGER.info(
                                "No schema in the URL. Prepending http://"
                            )
                            url = "http://" + entity.identifier
                            response = requests.get(
                                url, auth=(username, password), verify=ssl_verify
                            )

                    else:
                        try:
                            response = requests.get(url, verify=ssl_verify)
                        except requests.exceptions.InvalidSchema:
                            siemplify.LOGGER.info(
                                "No schema in the URL. Prepending http://"
                            )
                            url = "http://" + entity.identifier
                            response = requests.get(url, verify=ssl_verify)

                    siemplify.LOGGER.info(f"Response Code: {response.status_code}")
                    response.raise_for_status()

                    json_results[entity.identifier] = {
                        "data": response.text,
                        "redirects": [redirect.url for redirect in response.history],
                    }

                    successful_entities.append(entity.identifier)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )

                except Exception as e:
                    failed_entities.append(entity.identifier)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += "Successfully processed entities:\n   {}".format(
                "\n   ".join(successful_entities)
            )
            result_value = "true"

        if failed_entities:
            output_message += "\n\n Failed processing entities:\n   {}".format(
                "\n   ".join(failed_entities)
            )

        if not failed_entities and not successful_entities:
            output_message = "No entities were processed."

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"An error occurred while running action: {e}"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
