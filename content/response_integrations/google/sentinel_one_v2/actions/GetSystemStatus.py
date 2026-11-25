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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param
from ..core.constants import INTEGRATION_NAME, GET_SYSTEM_STATUS_SCRIPT_NAME
from ..core.SentinelOneV2Factory import SentinelOneV2ManagerFactory


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SYSTEM_STATUS_SCRIPT_NAME

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

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root, api_token=api_token, verify_ssl=verify_ssl
        )

        siemplify.LOGGER.info("Getting system status.")
        system_status = manager.get_system_status()

        siemplify.LOGGER.info("Getting DB system status")
        db_status = manager.get_db_system_status()

        siemplify.LOGGER.info("Getting cache server system status")
        cache_status = manager.get_cache_server_system_status()

        json_results = {
            "system_status": system_status.to_json(),
            "db_status": db_status.to_json(),
            "cache_status": cache_status.to_json(),
        }

        if system_status.is_ok and db_status.is_ok and cache_status.is_ok:
            output_message = "Successfully checked system status. No issues were found."
        else:
            output_message = (
                "Errors were found in the system, check SentinelOne instance status!"
            )

        if json_results:
            siemplify.result.add_result_json(json_results)

    except Exception as e:
        output_message = (
            f"Error executing action '{GET_SYSTEM_STATUS_SCRIPT_NAME}'. Reason: {e}"
        )
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
