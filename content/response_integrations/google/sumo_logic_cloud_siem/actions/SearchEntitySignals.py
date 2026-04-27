from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_dict_to_json_result_dict,
    convert_unixtime_to_datetime,
)
from ..core.SumoLogicCloudSIEMManager import SumoLogicCloudSIEMManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.SumoLogicCloudSIEMExceptions import InvalidTimeException
from ..core.constants import (
    INTEGRATION_NAME,
    SEARCH_ENTITY_SIGNALS_SCRIPT_NAME,
    DEFAULT_SEVERITY,
    DEFAULT_ACTION_LIMIT,
    ENTITY_TYPE_TO_QUERY,
)
from ..core.UtilsManager import get_timestamps


SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME, EntityTypes.USER]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_ENTITY_SIGNALS_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Key"
    )
    access_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access ID",
        print_value=True,
    )
    access_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Access Key"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # action parameters
    lowest_severity = extract_action_param(
        siemplify,
        param_name="Lowest Severity To Return",
        is_mandatory=False,
        print_value=True,
        default_value=DEFAULT_SEVERITY,
        input_type=int,
    )
    timeframe = extract_action_param(
        siemplify, param_name="Time Frame", is_mandatory=False, print_value=True
    )
    start_time_string = extract_action_param(
        siemplify, param_name="Start Time", is_mandatory=False, print_value=True
    )
    end_time_string = extract_action_param(
        siemplify, param_name="End Time", is_mandatory=False, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Signals To Return",
        is_mandatory=False,
        print_value=True,
        default_value=DEFAULT_ACTION_LIMIT,
        input_type=int,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    if lowest_severity < 1 or lowest_severity > 10:
        siemplify.LOGGER.info(
            f'"Lowest Severity To Return" must be between 1 and 10. Using default of {DEFAULT_SEVERITY}.'
        )
        lowest_severity = DEFAULT_SEVERITY

    if limit < 1:
        siemplify.LOGGER.info(
            f'"Max Signals To Return" must be non-negative. Using default of {DEFAULT_ACTION_LIMIT}.'
        )
        limit = DEFAULT_ACTION_LIMIT

    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    missing_entities = []
    failed_entities = []
    json_results = {}
    output_message = ""
    result_value = True

    try:
        alert_start_time = convert_unixtime_to_datetime(
            int(siemplify._current_alert.additional_properties.get("StartTime"))
        )
        alert_end_time = convert_unixtime_to_datetime(
            int(siemplify._current_alert.additional_properties.get("EndTime"))
        )

        start_time, end_time = get_timestamps(
            range_string=timeframe,
            start_time_string=start_time_string,
            end_time_string=end_time_string,
            alert_start_time=alert_start_time,
            alert_end_time=alert_end_time,
        )

        manager = SumoLogicCloudSIEMManager(
            api_root=api_root,
            api_key=api_key,
            access_id=access_id,
            access_key=access_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            force_check_connectivity=True,
        )

        for entity in siemplify.target_entities:
            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                siemplify.LOGGER.info(f"Fetching signals for {entity.identifier}")

                signals = manager.get_signals(
                    start_time=start_time,
                    end_time=end_time,
                    lowest_severity=lowest_severity,
                    entity_type=ENTITY_TYPE_TO_QUERY.get(entity.entity_type),
                    entity_identifier=entity.identifier,
                    limit=limit,
                )

                siemplify.LOGGER.info(
                    f"Found {len(signals)} signals for {entity.identifier}"
                )

                json_results[entity.identifier] = [
                    signal.to_json() for signal in signals
                ]
                if signals:
                    successful_entities.append(entity)
                else:
                    missing_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except Exception as e:
                failed_entities.append(entity)
                json_results[entity.identifier] = {"error": e}
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += "Successfully returned signals for the following entities in Sumo Logic Cloud SIEM:\n{}\n\n".format(
                "\n".join([entity.identifier for entity in successful_entities])
            )

        if missing_entities:
            output_message += "No signals were found for the following entities in Sumo Logic Cloud SIEM:\n{}\n\n".format(
                "\n".join([entity.identifier for entity in missing_entities])
            )

        if failed_entities:
            output_message += "Action wasn't able to retrieve signals for the following entities in Sumo Logic Cloud SIEM:\n{}".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )

        if not successful_entities:
            result_value = False
            if not failed_entities and missing_entities:
                output_message = "No signals were found for the provided entities in Sumo Logic Cloud SIEM."
            elif not missing_entities and failed_entities:
                output_message = "Action wasn't able to retrieve signals for the provided entities in Sumo Logic Cloud SIEM."
            elif not missing_entities and not failed_entities:
                output_message = "No suitable entities were found in the scope."

        if successful_entities or failed_entities or missing_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

    except InvalidTimeException:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{SEARCH_ENTITY_SIGNALS_SCRIPT_NAME}". Reason: "Start Time" '
            f'should be provided, when "Custom" is selected in "Time Frame" parameter.'
        )

    except Exception as e:
        siemplify.LOGGER.error(
            f'Error executing action "{SEARCH_ENTITY_SIGNALS_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f'Error executing action "{SEARCH_ENTITY_SIGNALS_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
