from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.PanoramaManager import PanoramaManager
from TIPCommon import extract_configuration_param, extract_action_param
import json

SCRIPT_NAME = "Panorama - RemoveIpFromGroup"
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
    group = extract_action_param(
        siemplify, param_name="Address Group Name", is_mandatory=True, print_value=True
    )

    ipsToRemove = set()
    json_results = []
    result_value = "true"
    output_message = ""
    successful_entities = []
    failed_entities = []

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            ipsToRemove.add(entity.identifier)

    if ipsToRemove:
        api = PanoramaManager(
            server_address, username, password, verify_ssl, siemplify.run_folder
        )
        for ip in ipsToRemove:
            siemplify.LOGGER.info(f"Process entity: {ip} Started")
            try:
                api.EditBlockedIpsInGroup(
                    deviceName=deviceName,
                    deviceGroupName=device_group_name,
                    groupName=group,
                    IpsToRemove=[ip],
                )
                successful_entities.append(ip)
                siemplify.LOGGER.info(f"Successfully removed entity: {ip} from {group}")
            except Exception as error:
                siemplify.LOGGER.error(
                    f"Unable to remove entity: {ip}. Reason is: {error}"
                )
                failed_entities.append(ip)

        json_results = api.ListAddressesInGroup(
            deviceName=deviceName, deviceGroupName=device_group_name, groupName=group
        )

        if successful_entities:
            output_message += (
                "Successfully removed the following IPs from the Palo Alto Panorama address group "
                '"{}": {}'.format(
                    group, "\n".join([entity for entity in successful_entities])
                )
            )

        if failed_entities:
            output_message += (
                "\n\nAction was not able to remove the following IPs from the Palo Alto Panorama "
                'address group "{}": {}'.format(
                    group, "\n".join([entity for entity in failed_entities])
                )
            )

        if not successful_entities:
            output_message = f'No IPs were removed from the Palo Alto Panorama address group "{group}"'
            result_value = "false"

    else:
        output_message = "No IPs found"
        siemplify.LOGGER.info(output_message)
        result_value = "false"

    siemplify.result.add_result_json(json.dumps(list(json_results)))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
