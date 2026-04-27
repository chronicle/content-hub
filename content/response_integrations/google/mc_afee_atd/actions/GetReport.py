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

import base64
import json
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.Siemplify import InsightSeverity, InsightType
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import GET_REPORT_SCRIPT_NAME, INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME
from ..core.McAfeeATDManager import READY_STATUSES, McAfeeATDManager, McAfeeATDManagerError

PDF_FILE_NAME = "{0}.pdf"
PDF_FILE_HEADER = "{0} PDF Report"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.action_definition_name = GET_REPORT_SCRIPT_NAME
    siemplify.script_name = GET_REPORT_SCRIPT_NAME

    # Parameters
    task_ids = extract_action_param(siemplify, param_name="Task IDs", print_value=True)
    siemplify.LOGGER.info("Start Get report Action.")
    output_message = "Searching reports for task ids."

    siemplify.end(output_message, task_ids, EXECUTION_STATE_INPROGRESS)


def fetch_scan_report_async():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_REPORT_SCRIPT_NAME

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
        is_mandatory=True,
        print_value=True,
    )

    # Parameters
    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", print_value=True, input_type=bool
    )

    result_value = False

    try:
        atd_manager = McAfeeATDManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        # Extract TASK IDS
        task_ids = extract_action_param(
            siemplify, param_name="additional_data", default_value=""
        )
        task_ids_list = (
            [item.strip() for item in task_ids.split(",")] if task_ids else []
        )

        is_ready = True
        results = []

        for task_id in task_ids_list:
            try:
                # check if analysis completed
                status = atd_manager.get_task_id_status(task_id)
                if status not in READY_STATUSES:
                    is_ready = False

            except Exception as err:
                error_message = (
                    f'Cannot get status for task ID "{task_id}", Error: {err}'
                )
                siemplify.LOGGER.error(error_message)
                siemplify.LOGGER.exception(err)

        if is_ready:
            json_results = {}
            successful_task_ids = []
            failed_task_ids = []
            non_existing_reports_task_ids = []

            for task_id in task_ids_list:
                try:
                    siemplify.LOGGER.info(f"Task {task_id} is ready. Fetching report")
                    # Get analysis report
                    json_report = atd_manager.get_json_report(task_id)
                    pdf_report = atd_manager.get_pdf_report(task_id)

                    if create_insight:
                        try:
                            txt_report = atd_manager.get_txt_report(task_id)
                            if txt_report:
                                siemplify.create_case_insight(
                                    triggered_by=INTEGRATION_NAME,
                                    title=f"Report {task_id} Summary",
                                    content=txt_report,
                                    entity_identifier="",
                                    severity=InsightSeverity.INFO,
                                    insight_type=InsightType.General,
                                )
                        except McAfeeATDManagerError as err:
                            siemplify.LOGGER.exception(err)
                            non_existing_reports_task_ids.append(task_id)
                            continue

                    if json_report:
                        json_results[task_id] = json_report
                        results.append(json_report["Summary"])
                    if pdf_report:
                        siemplify.result.add_attachment(
                            PDF_FILE_HEADER.format(task_id),
                            PDF_FILE_NAME.format(task_id),
                            base64.b64encode(pdf_report).decode("utf-8"),
                        )

                    result_value = json.dumps(results)
                    siemplify.result.add_result_json(json.dumps(json_results))
                    successful_task_ids.append(task_id)

                except McAfeeATDManagerError as e:
                    failed_task_ids.append(task_id)
                    siemplify.LOGGER.error(e)
                    siemplify.LOGGER.exception(e)

                except Exception as err:
                    error_message = (
                        f'Error fetching report for task ID "{task_id}", Error: {err}'
                    )
                    siemplify.LOGGER.error(error_message)
                    siemplify.LOGGER.exception(err)
                    failed_task_ids.append(task_id)

            if successful_task_ids:
                output_message = (
                    f"Found reports for the following tasks in {INTEGRATION_DISPLAY_NAME}: "
                    f"{','.join(successful_task_ids)}"
                )

                if non_existing_reports_task_ids:
                    output_message += (
                        f"\nThe scanning was completed, but the report is not available. Please make "
                        f"sure that the scan was valid. Affected reports: "
                        f"{','.join(non_existing_reports_task_ids)}"
                    )

                if failed_task_ids:
                    output_message += (
                        f"\nThe following tasks were not found in {INTEGRATION_DISPLAY_NAME}: "
                        f"{','.join(failed_task_ids)}"
                    )
            else:
                output_message = "No reports were found."
                result_value = False

            atd_manager.logout()
            status = EXECUTION_STATE_COMPLETED

        else:
            siemplify.LOGGER.info(f"Tasks {task_ids} are still queued for analysis.")
            output_message = f"Continuing...the requested items are still queued for analysis {task_ids}"
            atd_manager.logout()
            result_value = task_ids
            status = EXECUTION_STATE_INPROGRESS

    except Exception as err:
        output_message = (
            f"Error executing action {GET_REPORT_SCRIPT_NAME}. Reason: {err}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Get Report - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        fetch_scan_report_async()
