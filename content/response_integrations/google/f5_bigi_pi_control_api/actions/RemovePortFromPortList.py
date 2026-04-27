from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.F5BIGIPiControlAPIManager import F5BIGIPiControlAPIManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    REMOVE_PORT_FROM_PORT_LIST_SCRIPT_NAME,
)
from ..core.UtilsManager import convert_comma_separated_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_PORT_FROM_PORT_LIST_SCRIPT_NAME
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
    port_list_name = extract_action_param(
        siemplify, param_name="Port List Name", is_mandatory=True, print_value=True
    )
    ports_to_remove = extract_action_param(
        siemplify, param_name="Ports", is_mandatory=True, print_value=True
    )
    ports_to_remove = convert_comma_separated_to_list(ports_to_remove)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_ports = []
    non_existing_ports = []

    try:
        manager = F5BIGIPiControlAPIManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        port_list = manager.get_port_list(port_list_name=port_list_name)
        updated_ports_data = [
            port
            for port in port_list.ports
            if port.get("name", "") not in ports_to_remove
        ]

        if not updated_ports_data:
            raise Exception(f"you can't remove all of the ports from the port list.")

        updated_port_list = manager.update_port_list(
            port_list_name=port_list_name, ports=updated_ports_data
        )
        for port in ports_to_remove:
            if port not in [item.get("name") for item in updated_port_list.ports]:
                if port in [item.get("name") for item in port_list.ports]:
                    successful_ports.append(port)
                else:
                    non_existing_ports.append(port)

        if successful_ports:
            siemplify.result.add_result_json(updated_port_list.to_json())
            output_message += "Successfully removed the following ports from the {} port list in {}: \n{}".format(
                port_list_name, INTEGRATION_DISPLAY_NAME, "\n".join(successful_ports)
            )

        if non_existing_ports:
            output_message += "\n\nThe following ports didn't exist in {} port list in {}: \n{}".format(
                port_list_name, INTEGRATION_DISPLAY_NAME, "\n".join(non_existing_ports)
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {REMOVE_PORT_FROM_PORT_LIST_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{REMOVE_PORT_FROM_PORT_LIST_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
