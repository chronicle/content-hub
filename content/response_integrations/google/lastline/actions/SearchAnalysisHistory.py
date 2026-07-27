# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import validators
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.LastlineManager import LastlineManager
from ..core.consts import (
    INTEGRATION_NAME,
    SEARCH_ANALYSIS_HISTORY,
    DEFAULT_MAX_HOURS_BACKWARDS,
    DEFAULT_X_LAST_SCANS,
    DEFAULT_SKIP_X_FIRST_SCANS,
    SUBMISSION_TYPE_MAPPER,
    NOT_SPECIFIED,
    FILE,
    URL,
    SEARCH_RESULTS,
)
from ..core.utils import get_max_hours_backwards_as_date, get_file_hash
from ..core.exceptions import LastlineInvalidParamException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SEARCH_ANALYSIS_HISTORY}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=False,
        print_value=True,
    )

    submission_name = extract_action_param(
        siemplify, param_name="Submission Name", is_mandatory=False, print_value=True
    )

    submission_type = extract_action_param(
        siemplify, param_name="Submission Type", is_mandatory=False, print_value=True
    )

    if submission_type != NOT_SPECIFIED:
        submission_type = SUBMISSION_TYPE_MAPPER.get(submission_type, NOT_SPECIFIED)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        max_hours_backwards = extract_action_param(
            siemplify,
            param_name="Max Hours Backwards",
            is_mandatory=False,
            print_value=True,
            input_type=int,
            default_value=DEFAULT_MAX_HOURS_BACKWARDS,
        )

        if max_hours_backwards is not None:
            max_hours_backwards = get_max_hours_backwards_as_date(
                hours_backwards=max_hours_backwards
            )

        last_x_scans = extract_action_param(
            siemplify,
            param_name="Search in last x scans",
            is_mandatory=True,
            print_value=True,
            input_type=int,
            default_value=DEFAULT_X_LAST_SCANS,
        )

        first_x_scans = extract_action_param(
            siemplify,
            param_name="Skip first x scans",
            is_mandatory=True,
            print_value=True,
            input_type=int,
            default_value=DEFAULT_SKIP_X_FIRST_SCANS,
        )

        manager = LastlineManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        if submission_type == NOT_SPECIFIED and submission_name:
            submission_type = URL if validators.url(submission_name) else FILE
        elif submission_type == NOT_SPECIFIED and not submission_name:
            submission_type = None
        url = submission_name if submission_type == URL else None

        file_sha1 = None
        file_md5 = None
        if submission_type == FILE and submission_name:
            file_sha1, file_md5 = get_file_hash(submission_name)

        siemplify.LOGGER.info(f"Fetching analysis history from {INTEGRATION_NAME}.")
        analysis = manager.search_analysis_history(
            submission_type=submission_type,
            start_time=max_hours_backwards,
            search_in_last_x_scans=last_x_scans,
            skip_first_x_scans=first_x_scans,
            url=url,
            file_sha1=file_sha1,
            file_md5=file_md5,
        )
        siemplify.LOGGER.info(
            f"Successfully fetched analysis history from {INTEGRATION_NAME}"
        )

        if analysis.data:
            # JSON
            siemplify.result.add_result_json(analysis.as_json())

            # CSV
            csv_table = analysis.as_csv()
            siemplify.result.add_data_table(SEARCH_RESULTS, construct_csv(csv_table))

            output_message = f"Found {INTEGRATION_NAME} completed analysis tasks for the provided search parameters"
            result_value = True

        else:
            output_message = "No Lastline reports were found."
            result_value = False

        status = EXECUTION_STATE_COMPLETED

    except LastlineInvalidParamException as error:
        siemplify.LOGGER.error(error)
        result_value = False
        status = EXECUTION_STATE_COMPLETED
        output_message = f"No {INTEGRATION_NAME} reports were found."

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to find completed analysis tasks for the provided search parameters. Error is: "
            f"{error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
