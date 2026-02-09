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

from ..core.constants import PROVIDER_NAME, UPDATE_ALERT_SCRIPT_NAME
from ..core.exceptions import RecordedFutureUnauthorizedError
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

    siemplify.script_name = UPDATE_ALERT_SCRIPT_NAME

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

    alert_id = extract_action_param(
        siemplify,
        param_name="Alert ID",
        is_mandatory=True,
        print_value=True,
    )
    assign_to = extract_action_param(
        siemplify,
        param_name="Assign To",
        is_mandatory=False,
        print_value=True,
    )
    note = extract_action_param(
        siemplify,
        param_name="Note",
        is_mandatory=False,
        print_value=True,
    )
    alert_status = extract_action_param(
        siemplify,
        param_name="Status",
        is_mandatory=False,
        print_value=True,
    )
    alert_status = None if alert_status == "None" else alert_status

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    try:
        if alert_status is None and assign_to is None and note is None:
            raise Exception(
                f"Error executing action {UPDATE_ALERT_SCRIPT_NAME}."
                " Reason: at least one of the action parameters should have a provided value.",
            )

        manager = RecordedFutureManager(
            api_url=api_url,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )
        updated_alert = manager.update_alert(
            alert_id=alert_id,
            status=alert_status,
            assignee=assign_to,
            note=note,
        )
        siemplify.result.add_result_json(updated_alert)
        output_message += f"Successfully updated alert {alert_id} in Recorded Future."

    except Exception as err:
        output_message = f"Error executing action {UPDATE_ALERT_SCRIPT_NAME}. Reason: {err}"
        if isinstance(err, RecordedFutureUnauthorizedError):
            output_message = "Unauthorized - please check your API token and try again."
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
