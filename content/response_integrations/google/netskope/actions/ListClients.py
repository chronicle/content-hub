from __future__ import annotations
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NetskopeManagerFactory import NetskopeManagerFactory
from TIPCommon import extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

INTEGRATION_NAME = "Netskope"
LISTCLIENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - ListClients"
CSV_TABLE_NAME = "Netskope - Clients"
DEFAULT_LIMIT = 25


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LISTCLIENTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Parameters
    use_v2_api = extract_action_param(
        siemplify,
        param_name="Use V2 API",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=False, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
        input_type=int,
        print_value=True,
    )

    if limit <= 0:
        siemplify.LOGGER.info(
            f"The limit is less than zero, using default limit {DEFAULT_LIMIT} instead."
        )
        limit = DEFAULT_LIMIT

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    siemplify.LOGGER.info("Starting to perform the action")
    status = EXECUTION_STATE_FAILED
    json_results = []
    output_clients = ""
    csv_table = []

    try:
        netskope_manager = NetskopeManagerFactory.get_manager(
            siemplify, api_version="v2" if use_v2_api else "v1"
        )
        clients_gen = netskope_manager.get_clients(query=query, limit=limit)
        clients = list(clients_gen)

        output_message = f"Found {len(clients)} clients"

        for client in clients:
            csv_table.append(client.to_table_data())
            json_results.append(client.to_json())

        if clients:
            siemplify.result.add_result_json(json_results)
            siemplify.result.add_data_table(
                title=CSV_TABLE_NAME, data_table=construct_csv(csv_table)
            )

        output_clients = json.dumps(json_results)
        siemplify.LOGGER.info("Finished performing the action")
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f'Error executing action "ListClients". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, output_clients, status)


if __name__ == "__main__":
    main()
