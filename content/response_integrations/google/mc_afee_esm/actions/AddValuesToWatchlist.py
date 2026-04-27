from __future__ import annotations
from ..core.McAfeeESMManager import McAfeeESMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    convert_comma_separated_to_list,
)
from ..core.constants import ADD_VALUES_TO_WATCHLIST_SCRIPT_NAME, INTEGRATION_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_VALUES_TO_WATCHLIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        remove_whitespaces=False,
        is_mandatory=True,
    )
    product_version = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Product Version",
        is_mandatory=True,
        print_value=True,
    )
    use_aes_encryption = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use AES Encryption",
        input_type=bool,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    watchlist_name = extract_action_param(
        siemplify, param_name="Watchlist Name", is_mandatory=True, print_value=True
    )
    values_to_add = extract_action_param(
        siemplify, param_name="Values to Add", is_mandatory=True, print_value=True
    )
    values_to_add = convert_comma_separated_to_list(values_to_add)
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = McAfeeESMManager(
            api_root=api_root,
            username=username,
            password=password,
            product_version=product_version,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            siemplify_scope=siemplify,
            use_aes_encryption=use_aes_encryption,
        )
        watchlist = manager.get_watchlist(watchlist_name)
        manager.add_values_to_watchlist(watchlist.watchlist_id, values_to_add)
        result_value = True
        output_message = "Successfully added values to the watchlist."
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {ADD_VALUES_TO_WATCHLIST_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result_value: {result_value}")
    siemplify.LOGGER.info(f"Output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
