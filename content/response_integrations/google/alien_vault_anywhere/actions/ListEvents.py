from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_datetime_to_unix_time
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.AlienVaultManagerLoader import AlienVaultManagerLoader
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
import datetime

INTEGRATION_NAME = "AlienVaultAnywhere"
SCRIPT_NAME = "List Events"
TIMESTAMP_FORMAT = "%d/%m/%Y"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    version = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Product Version",
        is_mandatory=True,
        default_value="V1",
    )
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        default_value=True,
        input_type=bool,
    )

    account_name = extract_action_param(
        siemplify,
        param_name="Account Name",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    event_name = extract_action_param(
        siemplify,
        param_name="Event Name",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    source_name = extract_action_param(
        siemplify,
        param_name="Source Name",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    start_time = extract_action_param(
        siemplify,
        param_name="Start Time",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    end_time = extract_action_param(
        siemplify,
        param_name="End Time",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    suppressed = extract_action_param(
        siemplify,
        param_name="Suppressed",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    events_limit = extract_action_param(
        siemplify,
        param_name="Events Limit",
        is_mandatory=False,
        input_type=int,
        print_value=True,
        default_value=100,
    )

    if version == "V1":
        siemplify.end(
            "This action is not supported for AlienVault Anywhere V1 integration. Please use V2.",
            "false",
            EXECUTION_STATE_FAILED,
        )

    if start_time:
        try:
            start_time = convert_datetime_to_unix_time(
                datetime.datetime.strptime(start_time, TIMESTAMP_FORMAT)
            )
        except ValueError:
            siemplify.LOGGER.error(
                f"Unable to parse start time {start_time}. Valid format is DD/MM/YYYY."
            )
            siemplify.end(
                f"Unable to parse start time {start_time}. Valid format is DD/MM/YYYY.",
                "false",
                EXECUTION_STATE_FAILED,
            )

    if end_time:
        try:
            end_time = convert_datetime_to_unix_time(
                datetime.datetime.strptime(end_time, TIMESTAMP_FORMAT)
            )
        except ValueError:
            siemplify.LOGGER.error(
                f"Unable to parse end time {end_time}. Valid format is DD/MM/YYYY."
            )
            siemplify.end(
                f"Unable to parse end time {end_time}. Valid format is DD/MM/YYYY.",
                "false",
                EXECUTION_STATE_FAILED,
            )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    json_results = []
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    try:
        alienvault_manager = AlienVaultManagerLoader.load_manager(
            version=version,
            api_root=server_address,
            username=username,
            password=password,
            use_ssl=use_ssl,
            chronicle_soar=siemplify,
        )
        siemplify.LOGGER.info("Fetching events.")
        events = alienvault_manager.get_events(
            start_time=start_time,
            end_time=end_time,
            account_name=account_name,
            event_name=event_name,
            source_name=source_name,
            limit=events_limit,
            suppressed=suppressed,
        )

        siemplify.LOGGER.info(f"Found {len(events)} events")
        siemplify.result.add_data_table(
            "Events", construct_csv([event.to_csv() for event in events])
        )
        json_results = [event.raw_data for event in events]
        output_message = (
            f"Successfully returned {len(events)} AlienVault Anywhere events"
        )

        alienvault_manager.session.close()

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to list Alien Vault Anywhere events! Error is {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to list Alien Vault Anywhere events! Error is {e}"

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
