from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.PanoramaManager import PanoramaManager, PanoramaException
from TIPCommon import extract_configuration_param, extract_action_param
import json

SCRIPT_NAME = "Panorama - UnblockIPsInPolicy"
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
    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", is_mandatory=True, print_value=True
    )
    target = extract_action_param(
        siemplify, param_name="Target", is_mandatory=True, print_value=True
    )

    if not target != "source" and not target != "destination":
        raise PanoramaException("Target must be source or destination!")

    ipToUnBlock = set()
    json_results = []
    result_value = "true"
    output_message = ""
    successful_entities = []
    failed_entities = []

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            ipToUnBlock.add(entity.identifier)

    if ipToUnBlock:
        api = PanoramaManager(
            server_address, username, password, verify_ssl, siemplify.run_folder
        )
        for ip in ipToUnBlock:
            siemplify.LOGGER.info(f"Process entity: {ip} Started")
            try:
                api.EditBlockedIps(
                    deviceName=deviceName,
                    deviceGroupName=device_group_name,
                    policyName=policy_name,
                    target=target,
                    IpsToRemove=[ip],
                )
                successful_entities.append(ip)
                siemplify.LOGGER.info(
                    f"Successfully unblocked entity: {ip} from {policy_name}"
                )
            except Exception as error:
                failed_entities.append(ip)
                siemplify.LOGGER.error(
                    f"Unable to unblock entity: {ip}. Reason is: {error}"
                )

        json_results = api.FindRuleBlockedIps(
            deviceName, device_group_name, policy_name, target
        )

        if successful_entities:
            output_message += (
                'Successfully unblocked the following IPs in the Palo Alto Panorama policy "{}": '
                "{}".format(
                    policy_name, "\n".join([entity for entity in successful_entities])
                )
            )

        if failed_entities:
            output_message += (
                "\n\nAction was not able to unblock the following IPs in the Palo Alto Panorama "
                'policy "{}": {}'.format(
                    policy_name, "\n".join([entity for entity in failed_entities])
                )
            )

        if not successful_entities:
            output_message = f'No IPs were unblocked in the Palo Alto Panorama policy "{policy_name}"'
            siemplify.LOGGER.info(output_message)
            result_value = "false"

    else:
        output_message = "No IPs found"
        result_value = "false"

    siemplify.result.add_result_json(json.dumps(list(json_results)))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
