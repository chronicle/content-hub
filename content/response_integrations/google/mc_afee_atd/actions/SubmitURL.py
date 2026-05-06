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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, dict_to_flat, output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME, SUBMIT_URL_SCRIPT_NAME
from ..core.McAfeeATDManager import DEFAULT_THRESHOLD, READY_STATUSES, McAfeeATDManager
from ..core.utils import get_entity

TABLE_NAME = "Result Task IDs"
UNSUPPORTED_FILE = -1
PDF_FILE_NAME = "{0}.pdf"
PDF_FILE_HEADER = "{0} PDF Report"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SUBMIT_URL_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_INPROGRESS

    try:
        atd_manager = McAfeeATDManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        # For tasks saving {url:task_id}
        task_ids = {}

        siemplify.LOGGER.info("Start Submit URL Action.")

        # Parameters
        analyzer_profile_id = extract_action_param(
            siemplify,
            param_name="Analyzer Profile ID",
            is_mandatory=True,
            print_value=True,
        )

        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.URL
        ]

        for entity in target_entities:
            try:
                task_id = atd_manager.submit_url(
                    entity.identifier.lower(), analyzer_profile_id
                )
                if task_id != UNSUPPORTED_FILE:
                    task_ids.update({entity.identifier: str(task_id)})
                else:
                    msg = f"Url-{entity.identifier.encode('utf-8')} is not supported"
                    raise Exception(
                        msg
                    )
            except Exception as err:
                error_message = (
                    f'Error submitting URL "{entity.identifier}", Error: {err}'
                )
                siemplify.LOGGER.error(error_message)
                siemplify.LOGGER.exception(err)

        # Provide logout from McAfee ATD.
        atd_manager.logout()
        output_message = "Searching reports for task ids."
        result_value = json.dumps(task_ids)

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SUBMIT_URL_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{SUBMIT_URL_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def fetch_scan_report_async():
    siemplify = SiemplifyAction()
    siemplify.script_name = SUBMIT_URL_SCRIPT_NAME

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

    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", print_value=True, input_type=bool
    )

    try:
        atd_manager = McAfeeATDManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        # Extract TASK IDS
        task_ids = json.loads(siemplify.parameters["additional_data"])
        threshold = (
            int(siemplify.parameters.get("Threshold", DEFAULT_THRESHOLD))
            if siemplify.parameters.get("Threshold")
            else DEFAULT_THRESHOLD
        )

        is_ready = True
        results = []
        entities_to_enrich = []

        for entity_identifier, task_id in task_ids.items():
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

            for entity_identifier, task_id in task_ids.items():
                try:
                    siemplify.LOGGER.info(f"Task {task_id} is ready. Fetching report")
                    # Get analysis report
                    json_report = atd_manager.get_json_report(task_id)
                    pdf_report = atd_manager.get_pdf_report(task_id)

                    entity = get_entity(
                        identifier=entity_identifier, entities=siemplify.target_entities
                    )
                    if create_insight:
                        txt_report = atd_manager.get_txt_report(task_id)

                        if txt_report:
                            siemplify.add_entity_insight(
                                entity,
                                txt_report,
                                triggered_by=INTEGRATION_DISPLAY_NAME,
                            )

                    json_results[entity_identifier] = json_report

                    if json_report.get("Summary"):
                        results.append(json_report["Summary"])
                        if entity:
                            entity.additional_properties.update(
                                dict_to_flat(json_report["Summary"])
                            )
                            entities_to_enrich.append(entity)

                            if (
                                int(
                                    json_report.get("Summary", {})
                                    .get("Verdict", {})
                                    .get("Severity", 0)
                                )
                                > threshold
                            ):
                                entity.is_suspicious = True

                    if pdf_report:
                        siemplify.result.add_attachment(
                            PDF_FILE_HEADER.format(task_id),
                            PDF_FILE_NAME.format(task_id),
                            base64.b64encode(pdf_report).decode("utf-8"),
                        )

                except Exception as err:
                    error_message = (
                        f'Error fetching report for task ID "{task_id}", Error: {err}'
                    )
                    siemplify.LOGGER.error(error_message)
                    siemplify.LOGGER.exception(err)

            if entities_to_enrich:
                output_message = (
                    "Target URLs were submitted and analyzed, entities were enriched."
                )
                result_value = json.dumps(results)
                siemplify.update_entities(entities_to_enrich)
            else:
                output_message = "No URLs were submitted."
                result_value = json.dumps({})
            atd_manager.logout()
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            status = EXECUTION_STATE_COMPLETED

        else:
            siemplify.LOGGER.info(
                f"Tasks {task_ids.values()} are still queued for analysis."
            )
            output_message = f"Continuing...the requested items are still queued for analysis {task_ids}"
            atd_manager.logout()
            result_value = json.dumps(task_ids)
            status = EXECUTION_STATE_INPROGRESS

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SUBMIT_URL_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{SUBMIT_URL_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Submit URL - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        fetch_scan_report_async()
