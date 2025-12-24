from __future__ import annotations

import json
import traceback

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.arcanna_client import ArcannaClient
from ..core.constants import SEND_ARCANNA_ANALYST_FEEDBACK_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEND_ARCANNA_ANALYST_FEEDBACK_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    arcanna_url = siemplify.extract_configuration_param(
        "Integration",
        "Url",
        is_mandatory=True,
    )
    api_key = siemplify.extract_configuration_param(
        "Integration",
        "Api Key",
        is_mandatory=True,
    )
    ssl_verify = str(
        siemplify.extract_configuration_param(
            "SSL Verification",
            "Api Key",
            is_mandatory=True,
        ),
    ).lower()
    ssl_verify = True if ssl_verify == "true" else False

    job_id = int(
        siemplify.extract_action_param("Job Id", print_value=True, is_mandatory=True),
    )
    event_id = str(
        siemplify.extract_action_param("Event Id", print_value=True, is_mandatory=True),
    )
    username = siemplify.extract_action_param(
        "Username",
        print_value=True,
        is_mandatory=True,
    )
    feedback = siemplify.extract_action_param(
        "Analyst Feedback",
        print_value=True,
        is_mandatory=True,
    )

    status = EXECUTION_STATE_COMPLETED
    output_message = f"{siemplify.script_name}: "
    result_value = True

    try:
        client = ArcannaClient(api_key=api_key, base_url=arcanna_url, verify=ssl_verify)
        response_json = client.send_feedback(
            job_id=job_id,
            event_id=event_id,
            username=username,
            arcanna_label=feedback,
        )
        output_message = (
            output_message + f"response={json.dumps(response_json, indent=2)}"
        )
        siemplify.result.add_result_json(response_json)
    except Exception as e:
        output_message = f"Error executing {siemplify.script_name}. Reason {e}."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(traceback.format_exc())
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.end(output_message, result_value, status)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )


if __name__ == "__main__":
    main()
