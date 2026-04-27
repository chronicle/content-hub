from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.CBEnterpriseEDRManager import (
    CBEnterpriseEDRManager,
    CBEnterpriseEDRUnauthorizedError,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

INTEGRATION_NAME = "CBEnterpriseEDR"
SCRIPT_NAME = "Get Events Associated With Process by Process Guid"
SUPPORTED_ENTITIES = [EntityTypes.PROCESS]


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

    process_guids = extract_action_param(
        siemplify,
        param_name="Process GUID",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    event_types = extract_action_param(
        siemplify,
        param_name="Search Criteria",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    query = extract_action_param(
        siemplify,
        param_name="Query",
        is_mandatory=True,
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

    if event_types:
        event_types = [event_type.strip() for event_type in event_types.split(",")]

    process_guids = [process_guid.strip() for process_guid in process_guids.split(",")]

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

        for process_guid in process_guids:
            try:
                siemplify.LOGGER.info(f"Started processing process: {process_guid}")

                siemplify.LOGGER.info(
                    f"Initializing events search for process {process_guid}"
                )
                events = cb_edr_manager.events_search(
                    process_guid=process_guid,
                    event_types=event_types,
                    query=query,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    timeframe=timeframe,
                    limit=record_limit,
                )

                json_results[process_guid] = [event.raw_data for event in events]

                if events:
                    siemplify.LOGGER.info(
                        f"Found {len(events)} results for {process_guid}"
                    )
                    siemplify.result.add_data_table(
                        f"Found events for process {process_guid}",
                        construct_csv([event.to_csv() for event in events]),
                    )
                    successful_entities.append(process_guid)

                else:
                    siemplify.LOGGER.info(f"No results were found for {process_guid}")
                    missing_entities.append(process_guid)

                siemplify.LOGGER.info(f"Finished processing process {process_guid}")

            except CBEnterpriseEDRUnauthorizedError as e:
                # Unauthorized - invalid credentials were passed. Terminate action
                siemplify.LOGGER.error(f"Failed to execute action! Error is {e}")
                siemplify.end(
                    f"Failed to execute action! Error is {e}",
                    "false",
                    EXECUTION_STATE_FAILED,
                )

            except Exception as e:
                failed_entities.append(process_guid)
                siemplify.LOGGER.error(f"An error occurred on process {process_guid}")
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += (
                "Found events for the following process guids:\n   {}".format(
                    "\n   ".join(successful_entities)
                )
            )
            result_value = "true"

        else:
            output_message += "No search results were returned."
            result_value = "false"

        if missing_entities:
            output_message += (
                "\n\nNo events were returned for the following entities:\n   {}".format(
                    "\n   ".join(missing_entities)
                )
            )

        if failed_entities:
            output_message += "\n\nFailed to get results because of the errors running search for the following process guids:\n   {}".format(
                "\n   ".join(failed_entities)
            )

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to execute action! Error is {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute action! Error is {e}"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
