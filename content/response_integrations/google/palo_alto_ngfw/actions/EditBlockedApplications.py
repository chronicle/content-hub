from __future__ import annotations
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import EDIT_BLOCKED_APPLICATIONS_SCRIPT_NAME, INTEGRATION_NAME
from ..core.NGFWManager import NGFWManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = EDIT_BLOCKED_APPLICATIONS_SCRIPT_NAME

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    deviceName = extract_action_param(
        siemplify, param_name="Device Name", print_value=True, is_mandatory=True
    )
    vsysName = extract_action_param(
        siemplify, param_name="Vsys Name", print_value=True, is_mandatory=True
    )
    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", print_value=True, is_mandatory=True
    )

    app2BlockInput = extract_action_param(
        siemplify,
        param_name="Applications To Block",
        print_value=True,
        default_value="",
    )
    app2UnBlockInput = extract_action_param(
        siemplify,
        param_name="Applications To UnBlock",
        print_value=True,
        default_value="",
    )
    app2Block = set()
    app2UnBlock = set()
    json_results = []

    for app in app2BlockInput.split(","):
        if app and (app not in app2Block):
            app2Block.add(app)

    for app in app2UnBlockInput.split(","):
        if app and (app not in app2Block):
            app2UnBlock.add(app)

    if app2Block or app2UnBlock:
        api = NGFWManager(
            api_root, username, password, siemplify.run_folder, verify_ssl
        )
        api.EditBlockedApplication(
            deviceName=deviceName,
            vsysName=vsysName,
            policyName=policy_name,
            applicationsToAdd=app2Block,
            applicationsToRemove=app2UnBlock,
        )

        json_results = api.FindRuleBlockedApplications(
            api.GetCurrenCanidateConfig(), deviceName, vsysName, policy_name
        )
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
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
