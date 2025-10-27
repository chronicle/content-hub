############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

# ============================================================================#
# title           :Ping.py                                          noqa: ERA001
# description     :This Module contains the Ping action
# author          :support@recordedfuture.com                       noqa: ERA001
# date            :10-31-2025
# python_version  :3.11                                             noqa: ERA001
# product_version :8.0
# ============================================================================#

from __future__ import annotations

import json
import sys
from typing import NoReturn

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, resume_stdout
from TIPCommon.extraction import extract_configuration_param

from ..core.constants import PING_SCRIPT_NAME, PROVIDER_NAME
from ..core.RecordedFutureManager import RecordedFutureManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    def end_script() -> NoReturn:
        output_object = siemplify._build_output_object()
        resume_stdout()
        sys.stdout.write(json.dumps(output_object))
        sys.exit()

    siemplify.end_script = end_script

    siemplify.script_name = PING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_url = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="ApiUrl",
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="ApiKey",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    recorded_future_manager = RecordedFutureManager(
        api_url,
        api_key,
        verify_ssl=verify_ssl,
    )

    output_message = "Connection Established."
    connectivity_result = True
    status = EXECUTION_STATE_COMPLETED
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        recorded_future_manager.test_connectivity()
        siemplify.LOGGER.info(
            f"Connection to API established, performing action {PING_SCRIPT_NAME}",
        )

    except Exception as e:
        output_message = f"An error occurred when trying to connect to the API: {e}"
        connectivity_result = False
        siemplify.LOGGER.error(
            f"Connection to API failed, performing action {PING_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.end(output_message, connectivity_result, status)


if __name__ == "__main__":
    main()
