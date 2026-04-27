from __future__ import annotations
import re
import urllib.parse

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon import extract_action_param, extract_configuration_param

from ..core.APIVoidManager import (
    APIVoidInvalidAPIKeyError,
    APIVoidManager,
    APIVoidManagerError,
    APIVoidNotFound,
)
from ..core.constants import GET_SCREENSHOT_SCRIPT_NAME, INTEGRATION_NAME, LIMIT_EXCEEDED


SUPPORTED_ENTITIES = [EntityTypes.URL]


def strip_scheme(url):
    parsed = urllib.parse.urlparse(url)
    scheme = f"{parsed.scheme}://"
    return parsed.geturl().replace(scheme, "", 1)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SCREENSHOT_SCRIPT_NAME
    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        input_type=str,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    # Parameters
    threshold = extract_action_param(
        siemplify,
        param_name="Threshold",
        is_mandatory=False,
        input_type=int,
        default_value=0,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""
    successful_entities = []
    missing_entities = []
    too_big_entities = []
    failed_entities = []
    json_results = {}
    status = EXECUTION_STATE_COMPLETED

    try:
        apivoid_manager = APIVoidManager(api_root, api_key, verify_ssl=verify_ssl)

        for entity in siemplify.target_entities:
            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        "Entity {0} is of unsupported type. "
                        "Skipping.".format(entity.identifier)
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                if not re.match(r"^[a-zA-Z]+://", entity.identifier):
                    siemplify.LOGGER.info(
                        "Seems like schema is missing from the URL. "
                        "Prepending http://"
                    )
                    url = "http://" + entity.identifier

                else:
                    url = entity.identifier

                siemplify.LOGGER.info(
                    "Capturing screenshot for " "entity {0}".format(entity.identifier)
                )
                screenshot_obj = apivoid_manager.get_url_screenshot(url)

                if screenshot_obj.file_size_bytes > 3 * 1000000:
                    siemplify.LOGGER.error(
                        "Screenshot size is larger than 3MB. "
                        "Unable to add screenshot as attachment."
                    )
                    too_big_entities.append(entity)
                    continue

                siemplify.result.add_attachment(
                    f"Screenshot - {entity.identifier}",
                    f"{strip_scheme(url)}_capture.{screenshot_obj.file_format}",
                    screenshot_obj.base64_file,
                )
                json_results[entity.identifier] = {
                    "file_md5_hash": screenshot_obj.file_md5_hash
                }
                successful_entities.append(entity)

            except APIVoidNotFound as e:
                siemplify.LOGGER.error(e)
                missing_entities.append(entity)

            except APIVoidInvalidAPIKeyError as e:
                siemplify.LOGGER.error(e)
                raise APIVoidInvalidAPIKeyError("API key is invalid.")

            except APIVoidManagerError as e:
                msg = str(e)
                siemplify.LOGGER.error(e)
                if LIMIT_EXCEEDED in msg.lower():
                    raise APIVoidManagerError(msg)

                failed_entities.append(entity)

            except Exception as e:
                failed_entities.append(entity)
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            successful_entities_data = "\n   ".join(
                [entity.identifier for entity in successful_entities]
            )
            output_message = (
                "{0}: Added screenshots for the following "
                "entities:\n   {1}\n\n".format(
                    INTEGRATION_NAME, successful_entities_data
                )
            )

            siemplify.update_entities(successful_entities)
            result_value = "true"

        if too_big_entities:
            too_big_entities_data = "\n   ".join(
                [entity.identifier for entity in too_big_entities]
            )
            output_message += (
                "Failed to add screenshots as attachments on the following "
                "entities:\n   {0}\n\n".format(too_big_entities_data)
            )

        if missing_entities:
            missing_entities_data = "\n   ".join(
                [entity.identifier for entity in missing_entities]
            )
            output_message += (
                "No screenshots were found for the following "
                "entities:\n   {0}\n\n".format(missing_entities_data)
            )

        if failed_entities:
            failed_entities_data = "\n   ".join(
                [entity.identifier for entity in failed_entities]
            )
            output_message += f"An error occurred on the following entities:\n   {failed_entities_data}"

        if not (
            successful_entities
            or failed_entities
            or missing_entities
            or too_big_entities
        ):
            output_message = "No URL entities found for capturing screenshots."

    except Exception as e:
        output_message = (
            f'Error executing action "{GET_SCREENSHOT_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
