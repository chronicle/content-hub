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
import json

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv
from TIPCommon.validation import ParameterValidator

from ..core.action_init import create_api_client
from ..core.consts import (
    DEFAULT_MAX_LIMIT,
    INTEGRATION_NAME,
    LIST_OU_SCRIPT_NAME,
    MIN_LIMIT,
    MAX_LIMIT,
    PARENT_ORG_UNIT_NOT_FOUND_ERR,
)
from ..core.exceptions import GSuiteValidationException, GSuiteNotFoundException
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_OU_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action configuration
    customer_id = extract_action_param(
        siemplify,
        param_name="Customer ID",
        is_mandatory=True,
        print_value=True,
    )
    organization_unit_path = extract_action_param(
        siemplify,
        param_name="Organization Unit Path",
        print_value=True,
    )
    max_organizational_units = extract_action_param(
        siemplify,
        param_name="Max Organization Units",
        input_type=int,
        default_value=DEFAULT_MAX_LIMIT,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_FAILED
    result_value = json.dumps([])

    try:
        validator = ParameterValidator(siemplify=siemplify)
        validator.validate_range(
            param_name="Max Organization Units",
            value=max_organizational_units,
            min_limit=MIN_LIMIT,
            max_limit=MAX_LIMIT,
        )
        gsuite_manager = create_api_client(siemplify)
        ou_list = gsuite_manager.list_ou(
            customer_id=customer_id,
            org_unit_path=organization_unit_path,
            max_results=max_organizational_units,
        )
        json_results = [ou.as_json() for ou in ou_list]
        siemplify.result.add_result_json(json_results)
        siemplify.result.add_data_table(
            "OU List", construct_csv([ou.as_csv() for ou in ou_list])
        )
        output_message = f"Successfully fetched organizational units."

        status = EXECUTION_STATE_COMPLETED
        result_value = json.dumps(json_results)

    except (GSuiteNotFoundException, GSuiteValidationException) as error:
        output_message = (
            f"Error executing action {LIST_OU_SCRIPT_NAME}. Reason: "
            "Customer ID was not found"
        )
        if (
            isinstance(error, GSuiteNotFoundException)
            and PARENT_ORG_UNIT_NOT_FOUND_ERR in str(error).lower()
        ):
            output_message = (
                f"Error executing action {LIST_OU_SCRIPT_NAME}. Reason: {error}"
            )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
    except Exception as error:
        output_message = (
            f"Error executing action {LIST_OU_SCRIPT_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
