from __future__ import annotations
from ..core.Office365CloudAppSecurityExceptions import Office365CloudAppSecurityNotFoundError
from ..core.Office365CloudAppSecurityManager import Office365CloudAppSecurityManager
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    convert_comma_separated_to_list,
)
from ..core.constants import CATEGORY_MAPPING

INTEGRATION_NAME = "Office365CloudAppSecurity"
SCRIPT_NAME = "Office365CloudAppSecurity - Create IP Address Range"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="portal URL",
        input_type=str,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API token",
        input_type=str,
    )

    # INIT ACTION PARAMETERS:
    name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, input_type=str
    )
    category = extract_action_param(
        siemplify, param_name="Category", is_mandatory=True, input_type=str
    )
    organization = extract_action_param(
        siemplify, param_name="Organization", is_mandatory=False, input_type=str
    )
    subnets = extract_action_param(siemplify, param_name="Subnets", is_mandatory=True)
    tags = extract_action_param(siemplify, param_name="Tags", is_mandatory=False)

    cloud_app_manager = Office365CloudAppSecurityManager(
        api_root=api_root, api_token=api_token
    )
    subnets = convert_comma_separated_to_list(subnets)
    tags = convert_comma_separated_to_list(tags)
    category = CATEGORY_MAPPING.get(category)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        ip_address_range_id = cloud_app_manager.create_ip_address_range(
            name, category, organization, subnets, tags
        )
        if ip_address_range_id:
            address_range_object = cloud_app_manager.get_ip_address_range(
                ip_address_range_id
            )
            if not address_range_object:
                raise Office365CloudAppSecurityNotFoundError(
                    "IP Address Range was not found"
                )
            siemplify.result.add_result_json(address_range_object.to_json())

            output_message = "Successfully created an IP Address Range in Microsoft Cloud App Security\n"
            status = EXECUTION_STATE_COMPLETED
            result_value = True
        else:
            output_message = f'Error executing action "{SCRIPT_NAME}". Reason: Failed to create IP address range\n'
            status = EXECUTION_STATE_FAILED
            result_value = False
    except Exception as error:
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {error}\n'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"Status: {status}\nResult Value: {result_value}\nOutput Message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
