from __future__ import annotations
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core import exceptions
from ..core.NetskopeManagerFactory import NetskopeManagerFactory
from TIPCommon import (
    extract_action_param,
    construct_csv,
    dict_to_flat,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

INTEGRATION_NAME = "Netskope"
LISTEVENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - ListEvents"
CSV_TABLE_NAME = "Netskope - Events"
DEFAULT_LIMIT = 100


def validate_alert_type(alert_type: str) -> None:
    """
    Validate Alert Type.

    :param alert_type: (str) The alert type.
    """
    if alert_type not in ["page", "application", "audit", "infrastructure"]:
        raise exceptions.NetskopeParamError("Invalid Event Type")


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LISTEVENTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Parameters
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=False, print_value=True
    )
    alert_type = extract_action_param(
        siemplify, param_name="Type", is_mandatory=False, print_value=True
    )
    time_period = extract_action_param(
        siemplify, param_name="Time Period", is_mandatory=False, print_value=True
    )
    start_time = extract_action_param(
        siemplify, param_name="Start Time", is_mandatory=False, print_value=True
    )
    end_time = extract_action_param(
        siemplify, param_name="End Time", is_mandatory=False, print_value=True
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
    output_events = ""

    try:
        if alert_type:
            validate_alert_type(alert_type=alert_type)
        netskope_manager = NetskopeManagerFactory.get_manager(
            siemplify, api_version="v2"
        )

        if alert_type:
            events_gen = netskope_manager.get_events(
                query=query,
                alert_type=alert_type,
                timeperiod=time_period,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        else:
            events_gen = netskope_manager.get_all_events(
                query=query,
                timeperiod=time_period,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                logger=siemplify.LOGGER,
            )

        events = list(events_gen)

        if events:
            output_message = f"Found {len(events)} events"
            json_results = events
            flat_events = list(map(dict_to_flat, events))
            csv_output = construct_csv(flat_events)
            siemplify.result.add_data_table(CSV_TABLE_NAME, csv_output)
            # add json
            siemplify.result.add_result_json(json.dumps(json_results))
            output_events = json.dumps(events)

        else:
            output_message = "Found 0 events, error: no events found"
            if isinstance(events, str):
                raise exceptions.NetskopeDataNotFoundError(events)

        siemplify.LOGGER.info("Finished performing the action")
        status = EXECUTION_STATE_COMPLETED

    except exceptions.NetskopeParamError as e:
        output_message = f"Failed to connect to the {INTEGRATION_NAME}! Error: {e}"
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = f'Error executing action "ListEvents". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, output_events, status)


if __name__ == "__main__":
    main()
