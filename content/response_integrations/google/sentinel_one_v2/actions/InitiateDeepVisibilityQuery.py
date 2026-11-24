from __future__ import annotations
import datetime
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    INITIATE_DEEP_VISIBILITY_QUERY_SCRIPT_NAME,
    QUERY_TIME_FORMAT,
)
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory

BACKWARDS_DAYS_TO_SEARCH = 30


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INITIATE_DEEP_VISIBILITY_QUERY_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    query_name = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )
    start_date = extract_action_param(
        siemplify, param_name="Start Date", print_value=True
    )
    end_date = extract_action_param(siemplify, param_name="End Date", print_value=True)

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if end_date:
            end_date_dt_obj = datetime.datetime.strptime(end_date, QUERY_TIME_FORMAT)
        else:
            end_date_dt_obj = (
                datetime.datetime.utcnow()
            )  # if end_date is not entered, using current time
            end_date = end_date_dt_obj.strftime(QUERY_TIME_FORMAT)
            siemplify.LOGGER.info(
                f"Using default end date of current time: {end_date} "
            )

        # if no start date is entered, using start date 30 days backwards from end_date
        if not start_date:
            start_date_dt_obj = end_date_dt_obj - datetime.timedelta(
                days=BACKWARDS_DAYS_TO_SEARCH
            )
            start_date = start_date_dt_obj.strftime(QUERY_TIME_FORMAT)
            siemplify.LOGGER.info(
                f"Using default start date of: {start_date}."
                "Start date is 30 days backwards from entered "
                "end_date or default end date."
            )

        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root, api_token=api_token, verify_ssl=verify_ssl
        )

        siemplify.LOGGER.info(
            f"Initiating deep visibility query with start date:"
            f"{start_date} and end data: {end_date}"
        )
        query_id = manager.initiate_deep_visibility_query(
            query_name=query_name, from_date=start_date, to_date=end_date
        )

        if query_id:
            siemplify.LOGGER.info(
                f"Successfully created a deep visibility query. Query ID : {query_id}"
            )
            siemplify.result.add_result_json({"query_id": query_id})
            output_message = (
                f"Successfully created a deep visibility query. Query ID : {query_id}"
            )

    except Exception as e:
        output_message = (
            "Error executing action"
            f"'{INITIATE_DEEP_VISIBILITY_QUERY_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n"
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
