from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.PanoramaManager import PanoramaManager
from TIPCommon import extract_configuration_param, extract_action_param
import json

SCRIPT_NAME = "Panorama - UnblockURLs"
PROVIDER_NAME = "Panorama"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Configuration.
    server_address = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Api Root"
    )
    username = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    # Parameters
    deviceName = extract_action_param(
        siemplify, param_name="Device Name", is_mandatory=True, print_value=True
    )
    device_group_name = extract_action_param(
        siemplify, param_name="Device Group Name", is_mandatory=True, print_value=True
    )
    category = extract_action_param(
        siemplify, param_name="URL Category Name", is_mandatory=True, print_value=True
    )

    urlToUnBlock = set()
    json_results = []
    result_value = "true"
    output_message = ""
    successful_entities = []
    failed_entities = []

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.URL:
            urlToUnBlock.add(entity.identifier.replace("&amp;", "&"))

    if urlToUnBlock:
        api = PanoramaManager(
            server_address, username, password, verify_ssl, siemplify.run_folder
        )
        for url in urlToUnBlock:
            try:
                siemplify.LOGGER.info(f"Removing url {url} from blacklist")
                api.RemoveBlockedUrls(
                    device_name=deviceName,
                    device_group_name=device_group_name,
                    policy_name=category,
                    urls_to_remove=[url],
                )
                siemplify.LOGGER.info(f"Successfully removed {url} from blacklist")
                successful_entities.append(url)
            except Exception as error:
                siemplify.LOGGER.info(f"Failed to block url {url}")
                siemplify.LOGGER.exception(error)
                failed_entities.append(url)

        json_results = api.FindRuleBlockedUrls(deviceName, device_group_name, category)

        if successful_entities:
            output_message += (
                "Successfully removed the following URLs from the Palo Alto Panorama URL Category "
                '"{}": {}'.format(
                    category, "\n".join([entity for entity in successful_entities])
                )
            )

        if failed_entities:
            output_message += (
                "\n\nAction was not able to remove the following URLs from the Palo Alto Panorama "
                'URL Category "{}": {}'.format(
                    category, "\n".join([entity for entity in failed_entities])
                )
            )

        if not successful_entities:
            output_message = f'No URLs were removed from the Palo Alto Panorama URL Category "{category}"'
            result_value = "false"

    else:
        output_message = "No URLs found"
        result_value = "false"

    siemplify.result.add_result_json(json.dumps(list(json_results)))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
