from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_dict_to_json_result_dict,
    unix_now,
    convert_unixtime_to_datetime,
)
from ..core.GoogleGRRManager import GoogleGRRManager
from ..core.consts import INTEGRATION_NAME, LIST_LAUNCHED_FLOWS
from ..core.exceptions import (
    GoogleGRRInvalidCredentialsException,
    GoogleGRRNotConnectedException,
    GoogleGRRNotFoundException,
)

SUPPORTED_ENTITIES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_LAUNCHED_FLOWS}"
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
    fetched_clients = []
    failed_to_fetch = []
    output_message = ""
    success_entities = []
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = GoogleGRRManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        for entity in siemplify.target_entities:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                #  Get Client ID of Entity
                siemplify.LOGGER.info(
                    f"Fetching Client ID of Entity: {entity.identifier}"
                )
                client = manager.get_client_id(
                    identifier=entity.additional_properties.get(
                        "OriginalIdentifier", entity.identifier
                    )
                )
                siemplify.LOGGER.info(
                    f"Successfully fetched Client ID of Entity: {entity.identifier}"
                )

                if not client:
                    raise GoogleGRRNotFoundException(
                        f"Failed to fetch flows for entity: {entity.identifier}"
                    )

                if client.client_id in fetched_clients:
                    siemplify.LOGGER.info(
                        f"Client ID: {client.client_id} already fetched"
                    )
                    continue

                fetched_clients.append(client.client_id)
                #  Get List of flows for client
                siemplify.LOGGER.info(
                    f"Fetching flows for Client with id: {client.client_id}"
                )
                flows_list = manager.list_launched_flows(
                    client_id=client.client_id,
                    max_results_to_return=max_results_to_return,
                    offset=offset,
                )
                siemplify.LOGGER.info(
                    f"Successfully fetched flows for Client with id: {client.client_id}"
                )

                #  Add result to csv and JSON
                json_flows = []
                for flow in flows_list:
                    json_flows.append(flow.as_json())
                    csv_list.append(flow.as_csv())

                if json_flows:
                    json_results[entity.identifier] = json_flows
                    success_entities.append(entity)

            except GoogleGRRInvalidCredentialsException as e:
                raise e

            except GoogleGRRNotConnectedException as e:
                raise e

            except GoogleGRRNotFoundException as e:
                failed_to_fetch.append(entity)
                siemplify.LOGGER.info(
                    f"Failed to fetch flows for entity: {entity.identifier}"
                )
                siemplify.LOGGER.error(
                    f"Failed to fetch flows for entity: {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            if json_results:
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results)
                )
                output_message = (
                    f"Successfully listed flows launched on the following entities:"
                    f" {' ,'.join([ent.identifier for ent in success_entities])}.\n"
                )

            if csv_list:
                siemplify.result.add_data_table(
                    "GRR Launched Flows", construct_csv(csv_list)
                )

            if failed_to_fetch:
                output_message += (
                    f"Could not list flows on the following entities:"
                    f" {' ,'.join([ent.identifier for ent in failed_to_fetch])}. \n"
                )

        if not json_results and not failed_to_fetch:
            output_message += "Could not list flows. No entities were found."

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action “{LIST_LAUNCHED_FLOWS}”. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
