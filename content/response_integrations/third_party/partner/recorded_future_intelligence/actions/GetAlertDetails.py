############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

import json
import sys
from typing import NoReturn

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, resume_stdout
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import GET_ALERT_DETAILS_SCRIPT_NAME, PROVIDER_NAME
from ..core.exceptions import (
    RecordedFutureNotFoundError,
    RecordedFutureUnauthorizedError,
)
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

    siemplify.script_name = GET_ALERT_DETAILS_SCRIPT_NAME
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

    alert_id = extract_action_param(siemplify, param_name="Alert ID", is_mandatory=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    is_success = False
    status = EXECUTION_STATE_FAILED

    try:
        recorded_future_manager = RecordedFutureManager(
            api_url,
            api_key,
            verify_ssl=verify_ssl,
        )
        alert_object = recorded_future_manager.get_information_about_alert(alert_id)
        siemplify.result.add_result_json(alert_object.to_json())
        siemplify.result.add_link("Web Report Link:", alert_object.alert_url)

        is_success = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            "Successfully fetched the following Alert ID details "
            f"from Recorded Future: \n{alert_id}"
        )

    except RecordedFutureUnauthorizedError as e:
        output_message = f"Unauthorized - please check your API token and try again. {e}"
    except RecordedFutureNotFoundError as e:
        output_message = (
            "Requested Alert ID wasn't found in Recorded Future, "
            "or something went wrong in executing "
            f"action {GET_ALERT_DETAILS_SCRIPT_NAME}. Reason: {e}"
        )
    except Exception as e:
        output_message = f"Error executing action {GET_ALERT_DETAILS_SCRIPT_NAME}. Reason: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {is_success}")
    siemplify.LOGGER.info(f"Status: {status}")

    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
