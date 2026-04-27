from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.PanoramaManager import PanoramaManager
from TIPCommon import extract_configuration_param, extract_action_param
import json

SCRIPT_NAME = "Panorama - GetBlockedApplications"
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    api = PanoramaManager(
        server_address, username, password, verify_ssl, siemplify.run_folder
    )
    config = api.GetCurrenCanidateConfig()

    siemplify.LOGGER.info(f"Fetching blocked applications from {PROVIDER_NAME}")
    currentApplications = api.FindRuleBlockedApplications(
        config=config,
        deviceName=deviceName,
        deviceGroupName=device_group_name,
        policyName=policy_name,
    )
    siemplify.LOGGER.info(
        f"Successfully fetched blocked applications from {PROVIDER_NAME}"
    )

    blockedApps = ", ".join(currentApplications)

    output_message = (
        'Successfully listed blocked applications in the policy "{}:\n {}'.format(
            policy_name, "\n".join(blockedApps.split(","))
        )
    )

    siemplify.result.add_result_json(json.dumps(list(currentApplications)))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, json.dumps(list(currentApplications)))


if __name__ == "__main__":
    main()
