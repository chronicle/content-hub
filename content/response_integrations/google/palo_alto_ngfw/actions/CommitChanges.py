from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import COMMIT_CHANGES_SCRIPT_NAME, INTEGRATION_NAME
from ..core.NGFWManager import NGFWManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = COMMIT_CHANGES_SCRIPT_NAME
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
    only_my_changes = extract_action_param(
        siemplify,
        param_name="Only My Changes",
        input_type=bool,
        print_value=True,
        is_mandatory=True,
    )

    api = NGFWManager(
        api_root, username, password, siemplify.run_folder, verify_ssl=verify_ssl
    )
    api.CommitChanges(only_my_changes=only_my_changes)

    siemplify.end("Successfully committed changes.", "true")


if __name__ == "__main__":
    main()
