from __future__ import annotations
from ..core.AWSCloudWatchManager import AWSCloudWatchManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.consts import (
    INTEGRATION_DISPLAY_NAME,
    LIST_LOG_GROUPS,
    LOG_GROUPS_TABLE_NAME,
    DEFAULT_MIN_GROUPS,
)
from ..core.exceptions import AWSCloudWatchInvalidParameterException

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_DISPLAY_NAME} - {LIST_LOG_GROUPS}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_DISPLAY_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_DISPLAY_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_DISPLAY_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = []
    csv_list = []

    try:
        manager = AWSCloudWatchManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )

        max_groups_to_return = extract_action_param(
            siemplify,
            param_name="Max Groups To Return",
            input_type=int,
            is_mandatory=False,
            print_value=True,
            default_value=50,
        )

        if max_groups_to_return < DEFAULT_MIN_GROUPS:
            raise AWSCloudWatchInvalidParameterException(
                f"'Max Groups to Return' should be greater than "
                f"{DEFAULT_MIN_GROUPS}."
            )

        siemplify.LOGGER.info(f"Fetching Log Groups from {INTEGRATION_DISPLAY_NAME}...")
        log_groups_list = manager.list_log_groups(
            max_groups_to_return=max_groups_to_return
        )
        siemplify.LOGGER.info(
            f"Successfully fetched Log Groups from {INTEGRATION_DISPLAY_NAME}."
        )

        siemplify.LOGGER.info(
            "Creating JSON and CSV table from the fetched log groups data..."
        )
        for log_group in log_groups_list:
            json_results.append(log_group.as_json())
            csv_list.append(log_group.as_csv())

        if json_results and csv_list:
            siemplify.result.add_result_json(json_results)
            siemplify.result.add_data_table(
                LOG_GROUPS_TABLE_NAME, construct_csv(csv_list)
            )
            output_message = (
                "Successfully returned available log groups in "
                f"{INTEGRATION_DISPLAY_NAME}"
            )
            siemplify.LOGGER.info(
                "Created JSON and CSV table from the fetched log groups data."
            )

        else:
            output_message = f"No log groups were found in {INTEGRATION_DISPLAY_NAME}"

        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f"Error executing action '{LIST_LOG_GROUPS}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
