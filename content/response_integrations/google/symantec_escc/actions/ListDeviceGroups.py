from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from symantec_escc.core.SymantecESCCManager import SymantecESCCManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from symantec_escc.core.constants import (
    INTEGRATION_NAME,
    LIST_DEVICE_GROUPS_ACTION,
    EQUAL_FILTER,
    CONTAINS_FILTER,
    DEFAULT_DEVICE_GROUPS_LIMIT,
)

TABLE_NAME = "Available Device Groups"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_DEVICE_GROUPS_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Groups To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_DEVICE_GROUPS_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if limit < 1:
            raise Exception('"Max Groups To Return" must be greater than 0.')

        manager = SymantecESCCManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        siemplify.LOGGER.info("Retrieving information about available device groups...")
        device_groups = manager.get_device_groups()
        if filter_value:
            if filter_logic == EQUAL_FILTER:
                device_groups = [
                    dev_group
                    for dev_group in device_groups
                    if dev_group.name == filter_value
                ]
            elif filter_logic == CONTAINS_FILTER:
                device_groups = [
                    dev_group
                    for dev_group in device_groups
                    if filter_value in dev_group.name
                ]
        device_groups = device_groups[:limit] if limit else device_groups
        if device_groups:
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([group.to_csv() for group in device_groups])
            )
            siemplify.result.add_result_json(
                [group.to_json() for group in device_groups]
            )
            output_message = (
                f"Successfully returned available device groups in {INTEGRATION_NAME}."
            )
        else:
            result_value = False
            output_message = f"No device groups were found based on the provided criteria in {INTEGRATION_NAME}."

    except Exception as e:
        output_message = f'Error executing action "List Device Groups". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
