from __future__ import annotations

import json
import traceback

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.arcanna_client import ArcannaClient
from ..core.constants import GET_ARCANNA_DECISION_SCRIPT_NAME


def dump(obj):
    for attr in dir(obj):
        print("obj.%s = %r" % (attr, getattr(obj, attr)))


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ARCANNA_DECISION_SCRIPT_NAME
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
    retry_count = (
        int(
            siemplify.extract_action_param(
                "Retry count",
                print_value=True,
                is_mandatory=True,
            ),
        )
        + 1
    )
    seconds_per_retry = float(siemplify.extract_action_param("Seconds per retry"))

    status = EXECUTION_STATE_COMPLETED
    output_message = f"{siemplify.script_name}: "
    result_value = True

    retrieval_finished = False
    client = ArcannaClient(api_key=api_key, base_url=arcanna_url, verify=ssl_verify)

    while client.retry_mechanism(retry_count, seconds_per_retry) is True:
        retry_count -= 1
        try:
            response_json = client.get_event_status(job_id=job_id, event_id=event_id)
            if response_json.get("status") == "pending_inference":
                siemplify.LOGGER.info("Decision still pending..")
                continue
            if response_json.get("status") == "ERROR":
                output_message = (
                    output_message
                    + f"ERROR response:{json.dumps(response_json, indent=2)}"
                )
                siemplify.LOGGER.error(output_message)
                status = EXECUTION_STATE_FAILED
                result_value = False
                retrieval_finished = True
                break
            if response_json.get("status", None) == "OK":
                output_message = (
                    output_message + f"response: {json.dumps(response_json, indent=2)}"
                )
                siemplify.result.add_result_json(response_json)
                retrieval_finished = True
                break
        except Exception as e:
            output_message = f"Error executing {siemplify.script_name}. Reason {e}."
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(traceback.format_exc())
            status = EXECUTION_STATE_FAILED
            result_value = False

    if not retrieval_finished:
        status = EXECUTION_STATE_FAILED
        output_message = (
            output_message
            + "Could not retrieve decision during configured retry period. Decision is not yet available. Try increasing the retry window.."
        )
        siemplify.LOGGER.warning(
            "Could not retrieve decision during configured retry period Decision is not yet available. Try increasing the retry window..",
        )

    siemplify.end(output_message, result_value, status)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )


if __name__ == "__main__":
    main()
