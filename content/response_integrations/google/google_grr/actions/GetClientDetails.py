from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.GoogleGRRManager import GoogleGRRManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.consts import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, GET_CLIENT_DETAILS
from ..core.exceptions import (
    GoogleGRRInvalidCredentialsException,
    GoogleGRRNotConnectedException,
)
from ..core import utils


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {GET_CLIENT_DETAILS}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
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

    client_ids = extract_action_param(
        siemplify, param_name="Client ID", is_mandatory=True, input_type=str
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    csv_list = []
    json_results = {}
    faild_to_fetch = []
    output_message = ""

    try:
        manager = GoogleGRRManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        # Split the detectors IDs
        client_ids = utils.load_csv_to_list(client_ids, "Client ID")

        siemplify.LOGGER.info(
            f"Fetching Clients details by id from {INTEGRATION_DISPLAY_NAME}"
        )

        for client_id in client_ids:
            try:
                siemplify.LOGGER.info(f"Fetching details of client with id:{client_id}")
                client_obj = manager.get_client_details(client_id)
                siemplify.LOGGER.info(
                    f"Successfully fetched details of client with id:{client_id}"
                )

                siemplify.LOGGER.info(
                    f"Processing details of client with id:{client_id}"
                )
                csv_list.append(client_obj.as_csv_by_id())
                json_results[client_id] = client_obj.as_json_by_id()
                siemplify.LOGGER.info(
                    f"Successfully processed details of client with id:{client_id}"
                )

            except GoogleGRRInvalidCredentialsException as e:
                raise e

            except GoogleGRRNotConnectedException as e:
                raise e

            except Exception as e:
                siemplify.LOGGER.error(
                    f"An error occurred when tried to fetch details of client: {client_id}"
                )
                siemplify.LOGGER.exception(e)
                faild_to_fetch.append(client_id)

        if json_results:
            output_message += (
                f"Successfully fetched details for the following clients: "
                + ", ".join(json_results.keys())
                + " \n"
            )
            json_results = convert_dict_to_json_result_dict(json_results)
            siemplify.result.add_result_json(json_results)
            siemplify.result.add_data_table(
                "GRR Clients Details", construct_csv(csv_list)
            )

        if faild_to_fetch:
            output_message += (
                f"Could not fetch details for the specified clients. {', '.join(faild_to_fetch)} "
                f"does not exist"
            )
        siemplify.LOGGER.info("Done processing client details by id")

        result_value = True if json_results else False
        status = EXECUTION_STATE_COMPLETED

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Error executing action '{GET_CLIENT_DETAILS}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f"Error executing action '{GET_CLIENT_DETAILS}'. Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
