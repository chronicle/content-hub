from __future__ import annotations
import datetime

from ..core.MandiantASMManager import MandiantASMManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    string_to_multi_value,
    unix_now,
)
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    SEARCH_ISSUES_SCRIPT_NAME,
    STATUS_MAPPING,
    DEFAULT_SEARCH_ISSUES_LIMIT,
    MAX_SEARCH_ISSUES_LIMIT,
    TIME_FRAME_MAPPING,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_ISSUES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    action_start_time = unix_now()

    # Integration parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
        remove_whitespaces=False,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        remove_whitespaces=False,
    )
    gti_api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="GTI API Key"
    )
    project_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Project Name"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    entity_name = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Entity Name", print_value=True, input_type=str
        )
    )
    issue_ids = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Issue IDs", print_value=True, input_type=str
        )
    )
    entity_ids = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Entity IDs", print_value=True, input_type=str
        )
    )
    tags = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Tags", print_value=True, input_type=str
        )
    )
    time_parameter = extract_action_param(
        siemplify, param_name="Time Parameter", print_value=True, input_type=str
    )
    time_frame = extract_action_param(
        siemplify, param_name="Time Frame", print_value=True, input_type=str
    )
    start_time_str = extract_action_param(
        siemplify, param_name="Start Time", print_value=True, input_type=str
    )
    end_time_str = extract_action_param(
        siemplify, param_name="End Time", print_value=True, input_type=str
    )
    lowest_severity = extract_action_param(
        siemplify,
        param_name="Lowest Severity To Return",
        print_value=True,
        input_type=str,
        is_mandatory=True,
    )
    lowest_severity = lowest_severity if lowest_severity != "Select One" else None

    status = extract_action_param(
        siemplify, param_name="Status", print_value=True, input_type=str
    )
    status = STATUS_MAPPING.get(status)

    limit = extract_action_param(
        siemplify,
        param_name="Max Issues To Return",
        print_value=True,
        default_value=DEFAULT_SEARCH_ISSUES_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    action_status = EXECUTION_STATE_COMPLETED
    output_message = f"No issues were found based on the provided criteria in {INTEGRATION_DISPLAY_NAME}."

    try:

        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError
        except ValueError:
            raise ValueError("Max Issues To Return must be a positive integer")

        if limit >= MAX_SEARCH_ISSUES_LIMIT:
            siemplify.LOGGER.info(
                f'Provided "Max Issues To Return" value is greater than allowed maximum, '
                f"{MAX_SEARCH_ISSUES_LIMIT} will be used instead"
            )
            limit = MAX_SEARCH_ISSUES_LIMIT

        end_time = datetime.datetime.now()

        if time_frame == "Custom":
            if not start_time_str:
                raise ValueError(
                    'Please specify the "Start Time" value for the custom interval'
                )

            start_time = datetime.datetime.fromisoformat(start_time_str)

            if end_time_str:
                end_time = datetime.datetime.fromisoformat(end_time_str)

        else:
            timedelta = TIME_FRAME_MAPPING[time_frame]
            start_time = datetime.datetime.now() - timedelta

        manager = MandiantASMManager(
            api_root=api_root,
            access_key=access_key,
            secret_key=secret_key,
            gti_api_key=gti_api_key,
            project_name=project_name,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        issues = manager.search_issues(
            lowest_severity=lowest_severity,
            limit=limit,
            script_starting_time=action_start_time,
            execution_deadline=siemplify.execution_deadline_unix_time_ms,
            entity_name=entity_name,
            issue_ids=issue_ids,
            entity_ids=entity_ids,
            tags=tags,
            time_parameter=time_parameter,
            start_time=start_time,
            end_time=end_time,
            status=status,
        )

        if issues:
            siemplify.result.add_result_json([issue.to_json() for issue in issues])
            result_value = True
            output_message = f"Successfully returned issues based on the provided criteria in {INTEGRATION_DISPLAY_NAME}."

    except Exception as e:
        result_value = False
        action_status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {SEARCH_ISSUES_SCRIPT_NAME}. Error is {e}"
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {action_status}"
        f"\n  is_success: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, action_status)


if __name__ == "__main__":
    main()
