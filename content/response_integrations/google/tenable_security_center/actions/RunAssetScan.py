from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import PROVIDER_NAME, RUN_ASSET_SCAN_SCRIPT_NAME
from ..core.TenableManager import TenableSecurityCenterManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.TenableExceptions import AssetNotFoundException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = RUN_ASSET_SCAN_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    server_address = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Server Address",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=False,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=False,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Access Key",
        is_mandatory=False,
        remove_whitespaces=False,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Secret Key",
        is_mandatory=False,
        remove_whitespaces=False,
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Use SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    scan_name = extract_action_param(
        siemplify, param_name="Scan Name", is_mandatory=True, print_value=True
    )
    asset_name = extract_action_param(
        siemplify, param_name="Asset Name", is_mandatory=True, print_value=True
    )
    policy_id = extract_action_param(
        siemplify,
        param_name="Policy ID",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    repository_id = extract_action_param(
        siemplify,
        param_name="Repository ID",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_messages = ""

    try:
        # Create manager instance
        manager = TenableSecurityCenterManager(
            server_address,
            username,
            password,
            access_key,
            secret_key,
            use_ssl,
        )
        result = manager.get_scan_results(
            scan_name, asset_name, policy_id, repository_id, description
        )

        if result:
            siemplify.result.add_result_json(result.to_json())
            output_messages = (
                f"Successfully started asset scan {asset_name} in Tenable.sc."
            )

    except AssetNotFoundException:
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_messages = f'Error executing action "Run Asset Scan". Reason: Asset {asset_name} was not found in Tenable.sc.'
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {RUN_ASSET_SCAN_SCRIPT_NAME}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_messages = f'Error executing action "Run Asset Scan". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Messages: {output_messages}")

    siemplify.end(output_messages, result_value, status)


if __name__ == "__main__":
    main()
