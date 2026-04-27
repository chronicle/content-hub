from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.F5BIGIPiControlAPIManager import F5BIGIPiControlAPIManager
from ..core.constants import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, CREATE_PORT_LIST_NAME
from ..core.UtilsManager import convert_comma_separated_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_PORT_LIST_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    list_name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, print_value=True
    )
    ports = extract_action_param(
        siemplify, param_name="Ports", is_mandatory=True, print_value=True
    )
    ports = convert_comma_separated_to_list(ports)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = F5BIGIPiControlAPIManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        port_list = manager.create_port_list(list_name=list_name, ports=ports)
        siemplify.result.add_result_json(port_list.to_json())
        output_message = (
            f"Successfully created port list {list_name} in {INTEGRATION_DISPLAY_NAME}."
        )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {CREATE_PORT_LIST_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{CREATE_PORT_LIST_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
