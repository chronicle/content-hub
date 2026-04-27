from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.GoogleGRRManager import GoogleGRRManager
from ..core.consts import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, LIST_CLIENTS


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_CLIENTS}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

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
        is_mandatory=False,
        print_value=True,
    )

    offset = extract_action_param(
        siemplify, param_name="Offset", is_mandatory=False, input_type=str
    )

    max_results_to_return = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        is_mandatory=False,
        default_value="5",
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = {}
    csv_list = []
    result_value = True

    try:
        manager = GoogleGRRManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        siemplify.LOGGER.info(f"Fetching {INTEGRATION_DISPLAY_NAME} Clients")
        client_objects = manager.list_clients(
            offset=offset, max_results_to_return=max_results_to_return
        )
        siemplify.LOGGER.info(
            f"Successfully Fetched clients from {INTEGRATION_DISPLAY_NAME} server with the provided "
            f"parameters!"
        )

        for client in client_objects:
            json_results[client.client_id] = client.as_json()
            csv_list.append(client.as_csv())

        if json_results:
            json_results = convert_dict_to_json_result_dict(json_results)
            siemplify.result.add_data_table("GRR Clients", construct_csv(csv_list))

        output_message = (
            f"Successfully listed available clients in {INTEGRATION_DISPLAY_NAME}"
            if json_results
            else f"No clients are available in GRR"
        )
        status = EXECUTION_STATE_COMPLETED

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action “{LIST_CLIENTS}”. Reason: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
