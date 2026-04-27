from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.PanoramaManager import PanoramaManager
from TIPCommon import extract_configuration_param, extract_action_param
import json

SCRIPT_NAME = "Panorama - EditBlockedApplication"
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
    app2BlockInput = extract_action_param(
        siemplify,
        param_name="Applications To Block",
        default_value="",
        is_mandatory=False,
        print_value=True,
    )
    app2UnBlockInput = extract_action_param(
        siemplify,
        param_name="Applications To UnBlock",
        default_value="",
        is_mandatory=False,
        print_value=True,
    )

    app2Block = set()
    app2UnBlock = set()
    json_results = []

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    for app in app2BlockInput.split(","):
        if app and (app not in app2Block):
            app2Block.add(app)

    for app in app2UnBlockInput.split(","):
        if app and (app not in app2Block):
            app2UnBlock.add(app)

    if app2Block or app2UnBlock:
        siemplify.LOGGER.info("Editing provided blocked/unblocked applications")
        api = PanoramaManager(
            server_address, username, password, verify_ssl, siemplify.run_folder
        )
        api.EditBlockedApplication(
            deviceName=deviceName,
            deviceGroupName=device_group_name,
            policyName=policy_name,
            applicationsToAdd=app2Block,
            applicationsToRemove=app2UnBlock,
        )
        siemplify.LOGGER.info(
            "Successfully edited provided blocked/unblocked applications"
        )

        siemplify.LOGGER.info("Finding rule blocked applications")
        json_results = api.FindRuleBlockedApplications(
            config=api.GetCurrenCanidateConfig(),
            deviceName=deviceName,
            deviceGroupName=device_group_name,
            policyName=policy_name,
        )
        siemplify.LOGGER.info("Successfully found rule blocked applications")

        output_message = "Following apps were affected:\n"

        if app2Block != set():
            output_message = output_message + f"Apps blocked: {','.join(app2Block)}\n"

        if app2UnBlock != set():
            output_message = (
                output_message + f"Apps unblocked: {','.join(app2UnBlock)}\n"
            )

        result_value = "true"

    else:
        output_message = "Nothing changed - no input"
        result_value = "false"

    siemplify.result.add_result_json(json.dumps(list(json_results)))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
