from __future__ import annotations
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import GET_BLOCKED_APPLICATIONS_SCRIPT_NAME, INTEGRATION_NAME
from ..core.NGFWManager import NGFWManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_BLOCKED_APPLICATIONS_SCRIPT_NAME
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

    api = NGFWManager(
        api_root, username, password, siemplify.run_folder, verify_ssl=verify_ssl
    )
    config = api.GetCurrenCanidateConfig()
    currentApplications = api.FindRuleBlockedApplications(
        config=config, deviceName=deviceName, vsysName=vsysName, policyName=policy_name
    )

    blockedApps = ", ".join(currentApplications)

    msg = "Current Blocked applications for {0}->{1}->{2}:\n {3}".format(
        deviceName, vsysName, policy_name, "\n".join(blockedApps.split(","))
    )

    output_message = msg

    siemplify.result.add_result_json(json.dumps(list(currentApplications)))
    siemplify.end(output_message, json.dumps(list(currentApplications)))


if __name__ == "__main__":
    main()
