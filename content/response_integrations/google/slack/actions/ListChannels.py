from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SlackManager import SlackManager, SlackManagerException, MaxRecordsException
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.consts import PROVIDER_NAME

SCRIPT_NAME = f"{PROVIDER_NAME} - ListChannels"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_token = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiToken", input_type=str
    )

    max_records_to_return = extract_action_param(
        siemplify,
        param_name="Max Channels to Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )

    type_of_channels = extract_action_param(
        siemplify,
        param_name="Type Filter",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", is_mandatory=False, print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", is_mandatory=False, print_value=True
    )
    filter_logic = extract_action_param(
        siemplify,
        param_name="Filter Logic",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = "false"

    try:
        slack_manager = SlackManager(api_token, siemplify=siemplify)
        slack_manager.validate_max_records(max_records_to_return)
        raw_channels = slack_manager.list_channels(types=type_of_channels)
        channels = slack_manager.filter_list_items(
            raw_channels,
            filter_key=filter_key,
            filter_value=filter_value,
            filter_logic=filter_logic,
            max_records_to_return=max_records_to_return,
        )
        output_message = f"{len(channels)} Channels have been received."
        if filter_logic == "Not Specified" or not filter_value:
            output_message += "\nThe filter was not applied, because parameter “Filter Value” has an empty value"
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.result.add_result_json([channel.raw_data for channel in channels])
        channels_table = [channel.to_csv() for channel in channels]
        # TODO: Remove if below after construct_csv with empty list fix
        if channels_table:
            siemplify.result.add_data_table(
                title="Channels", data_table=construct_csv(channels_table)
            )
        result = "true"
    except (SlackManagerException, MaxRecordsException, Exception) as e:
        output_message = f"Error executing action “List Channels”. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(f"Script Name: {SCRIPT_NAME} | {output_message}")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
