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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_CASE_EVIDENCE_SCRIPT_NAME,
    CASE_EVIDENCE_TABLE_NAME,
    LIST_OF_STATUS_EVIDENCE,
    TYPE_OF_EVIDENCE_MAPPING,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.LogRhythmManager import LogRhythmRESTManager
from ..core.utils import string_to_multi_value, validate_positive_integer


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_CASE_EVIDENCE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
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

    case_id = extract_action_param(
        siemplify, param_name="Case ID", is_mandatory=True, print_value=True
    )
    status_filter = extract_action_param(
        siemplify, param_name="Status Filter", print_value=True
    )
    type_filter = extract_action_param(
        siemplify, param_name="Type Filter", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Evidences To Return",
        default_value=50,
        print_value=True,
        input_type=int,
    )
    status_filter = status_filter.lower() if status_filter else None
    type_filter = type_filter.lower() if type_filter else None
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = (
        f"No evidence was found for the case with ID {case_id} in {INTEGRATION_NAME}."
    )

    try:
        validate_positive_integer(
            limit,
            err_msg="'Max Evidences To Return' parameter should be positive number.",
        )
        status_filter = get_validated_status(status_filter)
        type_filter = get_validated_type(type_filter)

        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        evidence_list = manager.get_case_evidence(
            case_id=case_id,
            status_filter=status_filter,
            type_filter=type_filter,
            limit=limit,
        )

        if evidence_list:
            siemplify.result.add_entity_table(
                CASE_EVIDENCE_TABLE_NAME.format(case_id),
                construct_csv([evidence.to_csv() for evidence in evidence_list]),
            )
            siemplify.result.add_result_json(
                [evidence.as_json() for evidence in evidence_list]
            )
            output_message = (f"Successfully listed evidence related to the case with "
                              f"ID {case_id} in {INTEGRATION_NAME}.")
            result_value = True

    except Exception as e:
        output_message = (
            f"Error executing action {LIST_CASE_EVIDENCE_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"is_success: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def get_validated_status(status_filter):
    for status in string_to_multi_value(status_filter):
        if status not in LIST_OF_STATUS_EVIDENCE:
            raise Exception(
                f"invalid values provided in the parameter 'Status Filter': "
                f"{status_filter}. Possible values: pending, completed, failed."
            )

    if status_filter:
        return status_filter.replace(" ", "")


def get_validated_type(type_filter):
    validated_type_filter = []
    for type in string_to_multi_value(type_filter):
        if type not in TYPE_OF_EVIDENCE_MAPPING.keys():
            raise Exception(
                f"invalid values provided in the parameter 'Type': {type_filter}. "
                f"Possible values: alarm, userEvents, log, note, file."
            )
        validated_type_filter.append(TYPE_OF_EVIDENCE_MAPPING.get(type))
    validated_type_filter = ",".join(validated_type_filter)
    if validated_type_filter:
        return validated_type_filter


if __name__ == "__main__":
    main()
