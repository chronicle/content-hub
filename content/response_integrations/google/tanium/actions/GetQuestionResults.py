from __future__ import annotations
import json
import sys
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyAction import SiemplifyAction
from tanium.core.TaniumManager import TaniumManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from tanium.core.constants import (
    INTEGRATION_NAME,
    GET_QUESTION_RESULTS_SCRIPT_NAME,
    MAX_QUESTION_RESULTS_DEFAULT,
    QUESTION_RESULT_TABLE_NAME,
)
from tanium.core.exceptions import TaniumNotFoundException
from tanium.core.utils import is_approaching_timeout


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = (
        unix_now()
        if is_first_run
        else json.loads(
            extract_action_param(
                siemplify, param_name="additional_data", default_value=str(unix_now())
            )
        )
    )
    siemplify.script_name = GET_QUESTION_RESULTS_SCRIPT_NAME
    mode = "Main" if is_first_run else "Get Report"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    question_id = extract_action_param(
        siemplify, param_name="Question ID", print_value=True, is_mandatory=True
    )
    create_case_wall = extract_action_param(
        siemplify,
        param_name="Create Case Wall Table",
        print_value=True,
        input_type=bool,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Rows to Return",
        input_type=int,
        print_value=True,
        default_value=MAX_QUESTION_RESULTS_DEFAULT,
        is_mandatory=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    result_value = False

    try:
        if limit <= 0:
            raise Exception(
                f'Invalid value was provided for "Max Rows to Return": {limit}. Positive number should be provided'
            )

        manager = TaniumManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        result = manager.get_question_result_full_data(
            question_id=question_id, limit=limit
        )

        if result.rows:
            result_value = True
            status = EXECUTION_STATE_COMPLETED
            output_message = f"Successfully fetched results for the following Tanium question id: {question_id}"
            siemplify.result.add_result_json(result.to_json())
            if create_case_wall:
                siemplify.result.add_data_table(
                    QUESTION_RESULT_TABLE_NAME.format(question_id),
                    construct_csv(result.to_csv_lines(multi_value_delimiter=" ")),
                )

        else:
            if is_approaching_timeout(
                action_start_time, siemplify.execution_deadline_unix_time_ms
            ):
                output_message = (
                    f"No results were found for the Tanium question id: {question_id}"
                )
                status = EXECUTION_STATE_COMPLETED
                end_action(siemplify, mode, output_message, result_value, status)
            else:
                status = EXECUTION_STATE_INPROGRESS
                output_message = f"Waiting for question results for the following Tanium question id: {question_id}"
                result_value = json.dumps(action_start_time)
    except Exception as e:
        output_message = (
            f"Error executing action {GET_QUESTION_RESULTS_SCRIPT_NAME}. Reason: {e}"
        )
        if isinstance(e, TaniumNotFoundException):
            output_message = (
                f"The question with ID {question_id} wasn't found in Tanium or it has "
                f"expired. Please check the spelling."
            )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    end_action(siemplify, mode, output_message, result_value, status)


def end_action(siemplify, mode, output_message, result_value, status):
    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
