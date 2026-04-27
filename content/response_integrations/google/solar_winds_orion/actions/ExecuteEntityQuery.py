from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.SolarWindsOrionConstants import (
    PROVIDER_NAME,
    EXECUTE_ENTITY_QUERY_SCRIPT_NAME,
    DEFAULT_IP_KEY,
    DEFAULT_HOSTNAME_KEY,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.SolarWindsOrionManager import SolarWindsOrionManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.SolarWindsOrionExceptions import FailedQueryException

TABLE_HEADER = "Results"
SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_ENTITY_QUERY_SCRIPT_NAME
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configurations
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="IP Address",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Parameters
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )
    ip_key = extract_action_param(
        siemplify,
        param_name="IP Entity Key",
        default_value=DEFAULT_IP_KEY,
        is_mandatory=False,
        print_value=True,
    )
    hostname_key = extract_action_param(
        siemplify,
        param_name="Hostname Entity Key",
        default_value=DEFAULT_HOSTNAME_KEY,
        is_mandatory=False,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = SolarWindsOrionManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if suitable_entities:
            query = manager.build_entity_query(
                query_string=query,
                entities=suitable_entities,
                ip_key=ip_key,
                hostname_key=hostname_key,
            )

            query_results = manager.execute_query(query=query)[:limit]

            if query_results:
                output_message = "Successfully executed query and retrieved results from SolarWinds Orion."
                siemplify.result.add_result_json(
                    {"results": [result.to_json() for result in query_results]}
                )
                result_value = True
                siemplify.result.add_data_table(
                    title=TABLE_HEADER,
                    data_table=construct_csv(
                        [result.to_csv() for result in query_results]
                    ),
                )
            else:
                output_message = "No results were retrieved from SolarWinds."
        else:
            output_message = "No entities were found in the scope."

    except FailedQueryException as e:
        output_message = (
            "Action wasn't able to successfully execute query and retrieve results from SolarWinds "
            "Orion. Reason: {}".format(e)
        )

    except Exception as e:
        output_message = f'Error executing action "Execute Entity Query". Reason: {e}'
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
