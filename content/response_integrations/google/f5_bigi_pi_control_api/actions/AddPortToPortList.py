from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.F5BIGIPiControlAPIManager import F5BIGIPiControlAPIManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ADD_PORT_TO_PORT_LIST_SCRIPT_NAME,
)
from ..core.UtilsManager import convert_comma_separated_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_PORT_TO_PORT_LIST_SCRIPT_NAME
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
    ports = extract_action_param(
        siemplify, param_name="Ports", is_mandatory=True, print_value=True
    )
    ports = convert_comma_separated_to_list(ports)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_ports = []
    failed_ports = []
    updated_port_list = None

    try:
        manager = F5BIGIPiControlAPIManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        for port in ports:
            siemplify.LOGGER.info(f"Started processing port: {port}")
            port_list = manager.get_port_list(port_list_name=port_list_name)
            list_ports = port_list.ports

            list_ports.append({"name": port})

            try:
                updated_port_list = manager.update_port_list(
                    port_list_name=port_list_name, ports=list_ports
                )
                if port in [item.get("name") for item in updated_port_list.ports]:
                    successful_ports.append(port)
                else:
                    failed_ports.append(port)
            except Exception as e:
                failed_ports.append(port)
                siemplify.LOGGER.error(f"Failed processing port:{port}")
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing port {port}")

        if successful_ports:
            siemplify.result.add_result_json(updated_port_list.to_json())
            output_message += "Successfully added the following ports to the {} port list in {}: \n{}".format(
                port_list_name, INTEGRATION_DISPLAY_NAME, "\n".join(successful_ports)
            )
        if failed_ports:
            output_message += "\nAction wasn't able to add the following ports to the {} port list in {}: \n{}".format(
                port_list_name, INTEGRATION_DISPLAY_NAME, "\n".join(failed_ports)
            )
        if not successful_ports:
            result = False
            output_message = f"No ports were added to the {port_list_name} port list in {INTEGRATION_DISPLAY_NAME}."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ADD_PORT_TO_PORT_LIST_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{ADD_PORT_TO_PORT_LIST_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
