from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.CBEnterpriseEDRManager import (
    CBEnterpriseEDRManager,
    CBEnterpriseEDRUnauthorizedError,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

INTEGRATION_NAME = "CBEnterpriseEDR"
SCRIPT_NAME = "Process Search"
SUPPORTED_ENTITIES = [EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    org_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization Key",
        is_mandatory=True,
        input_type=str,
    )
    api_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API ID",
        is_mandatory=True,
        input_type=str,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret Key",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    query = extract_action_param(
        siemplify,
        param_name="Query",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    timeframe = extract_action_param(
        siemplify,
        param_name="Time Frame",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    record_limit = extract_action_param(
        siemplify,
        param_name="Record limit",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )

    sort_by = extract_action_param(
        siemplify,
        param_name="Sort By",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    sort_order = extract_action_param(
        siemplify,
        param_name="Sort Order",
        is_mandatory=False,
        input_type=str,
        default_value="ASC",
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    json_results = {}
    failed_entities = []
    missing_entities = []
    output_message = ""

    try:
        cb_edr_manager = CBEnterpriseEDRManager(
            api_root, org_key, api_id, api_secret_key, verify_ssl
        )

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                siemplify.LOGGER.info(
                    f"Initializing process search for entity {entity.identifier}"
                )
                processes = cb_edr_manager.process_search(
                    query=query,
                    device_name=entity.identifier,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    timeframe=timeframe,
                    limit=record_limit,
                )

                json_results[entity.identifier] = [
                    process.raw_data for process in processes
                ]

                if processes:
                    siemplify.LOGGER.info(
                        f"Found {len(processes)} results for {entity.identifier}"
                    )
                    siemplify.result.add_data_table(
                        f"Process search results for {entity.identifier}",
                        construct_csv([process.to_csv() for process in processes]),
                    )
                    successful_entities.append(entity)

                else:
                    siemplify.LOGGER.info(
                        f"No results were found for {entity.identifier}"
                    )
                    missing_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except CBEnterpriseEDRUnauthorizedError as e:
                # Unauthorized - invalid credentials were passed. Terminate action
                siemplify.LOGGER.error(
                    f"Failed to execute Process Search action! Error is {e}"
                )
                siemplify.end(
                    f"Failed to execute Process Search action! Error is {e}",
                    "false",
                    EXECUTION_STATE_FAILED,
                )

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += (
                "Found process information for the following entities:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in successful_entities])
                )
            )
            siemplify.update_entities(successful_entities)
            result_value = "true"

        else:
            output_message += "No search results were returned."
            result_value = "false"

        if missing_entities:
            output_message += "\n\nNo search results were returned for the following entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in missing_entities])
            )

        if failed_entities:
            output_message += "\n\nFailed to get results because of the errors running search for the following entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in failed_entities])
            )

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to execute Process Search action! Error is {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute Process Search action! Error is {e}"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
