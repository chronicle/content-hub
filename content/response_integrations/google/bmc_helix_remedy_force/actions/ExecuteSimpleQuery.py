from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BMCHelixRemedyForceManager import BMCHelixRemedyForceManager
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    construct_csv,
    convert_comma_separated_to_list,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    EXECUTE_SIMPLE_ACTION,
    TIME_FRAME_CUSTOM,
    LIMIT_MAX,
)
from dateutil import parser


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_SIMPLE_ACTION

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Secret"
    )
    refresh_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Refresh Token"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    record_type = extract_action_param(
        siemplify, param_name="Record Type", print_value=True, is_mandatory=True
    )
    where_filter = extract_action_param(
        siemplify, param_name="Where Filter", print_value=True, is_mandatory=False
    )
    time_frame = extract_action_param(
        siemplify, param_name="Time Frame", print_value=True, is_mandatory=False
    )
    start_time = extract_action_param(
        siemplify, param_name="Start Time", print_value=True, is_mandatory=False
    )
    end_time = extract_action_param(
        siemplify, param_name="End Time", print_value=True, is_mandatory=False
    )
    fields_to_return = extract_action_param(
        siemplify, param_name="Fields To Return", print_value=True, is_mandatory=False
    )
    fields_to_return = convert_comma_separated_to_list(fields_to_return)

    sort_field = extract_action_param(
        siemplify,
        param_name="Sort Field",
        print_value=True,
        is_mandatory=False,
        default_value="CreatedDate",
    )
    sort_order = extract_action_param(
        siemplify, param_name="Sort Order", print_value=True, is_mandatory=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        limit = extract_action_param(
            siemplify,
            param_name="Max Results To Return",
            input_type=int,
            print_value=True,
            is_mandatory=False,
            default_value=50,
        )

        if limit and limit <= 0:
            siemplify.LOGGER.error(
                f'Given value of {limit} for parameter "Max Results To Return" is non positive.'
            )
            raise Exception(
                f'Given value of {limit} for parameter "Max Results To Return" is non positive'
            )

        if limit and limit > LIMIT_MAX:
            siemplify.LOGGER.error(
                f'The maximum limit for parameter "Max Results To Return" is {LIMIT_MAX}'
            )
            raise Exception(
                f'The maximum limit for parameter "Max Results To Return" is {LIMIT_MAX}'
            )

        if time_frame == TIME_FRAME_CUSTOM and start_time is None:
            siemplify.LOGGER.error(
                f'Missing value for parameter "Start Time" this value is mandatory when "Custom" is selected for parameter "Time Frame".'
            )
            raise Exception(
                f'Missing value for parameter "Start Time" this value is mandatory when "Custom" is selected for parameter "Time Frame"'
            )

        if time_frame == TIME_FRAME_CUSTOM and end_time is None:
            siemplify.LOGGER.error(
                f'Missing value for parameter "End Time" this value is mandatory when "Custom" is selected for parameter "Time Frame" the action will use the current time'
            )

        if time_frame == TIME_FRAME_CUSTOM and end_time and start_time:
            start_date = parser.parse(start_time)
            end_date = parser.parse(end_time)

            if start_date > end_date:
                raise Exception("End Time should be later than Start Time")

        manager = BMCHelixRemedyForceManager(
            api_root=api_root,
            password=password,
            username=username,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            login_api_root=login_api_root,
        )
        query = manager.build_query(
            record_type=record_type,
            where_filter=where_filter,
            time_frame=time_frame,
            start_time=start_time,
            end_time=end_time,
            fields_to_return=fields_to_return,
            sort_field=sort_field,
            sort_order=sort_order,
            limit=limit,
        )

        query_details = manager.execute_custom_query(query=query)

        if query_details.total_size > 0:
            siemplify.result.add_result_json(query_details.to_json())
            output_message = f'Successfully returned results for the query "{query}" in {INTEGRATION_NAME}.'
            siemplify.result.add_data_table(
                f"Results", data_table=construct_csv(query_details.to_table())
            )
        else:
            output_message = (
                f'No results were found for the query "{query}" in {INTEGRATION_NAME}.'
            )

    except Exception as e:
        output_message = f"Error executing action {EXECUTE_SIMPLE_ACTION}. Reason: {e}."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
