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

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
)

from ..core.FireEyeHXManager import FireEyeHXManager

INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Delete Bulk Acquisition"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
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
        default_value=True,
        input_type=bool,
    )

    bulk_id = extract_action_param(
        siemplify,
        param_name="Bulk Acquisition ID",
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"
    manager = None

    try:
        if not bulk_id or not str(bulk_id).strip():
            raise ValueError("Bulk Acquisition ID must not be empty.")

        try:
            clean_bulk_id = int(str(bulk_id).strip())
        except ValueError as value_error:
            raise ValueError(f"Bulk Acquisition ID must be a number, got: {bulk_id}.") from value_error

        manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        manager.delete_bulk_acquisition(clean_bulk_id)
        result_value = "true"
        output_message = f"Successfully deleted bulk acquisition {clean_bulk_id}."

    except Exception as err:
        output_message = f"Error executing {SCRIPT_NAME}: {err}"
        siemplify.LOGGER.exception(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = "false"

    finally:
        if manager:
            try:
                manager.logout()
            except Exception as logout_err:
                siemplify.LOGGER.warning(f"Failed to log out: {logout_err}")

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
