from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.arcanna_client import ArcannaClient
from ..core.constants import TRIGGER_TRAINING_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = TRIGGER_TRAINING_SCRIPT_NAME
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
        siemplify.extract_action_param("Job ID", print_value=True, is_mandatory=True),
    )
    username = siemplify.extract_action_param(
        "Username",
        print_value=True,
        is_mandatory=True,
    )

    status = EXECUTION_STATE_COMPLETED
    output_message = f"{siemplify.script_name}:"

    try:
        client = ArcannaClient(api_key=api_key, base_url=arcanna_url, verify=ssl_verify)
        response_json = client.train_model(job_id=job_id, username=username)
        result_value = True
        output_message = output_message + f"response={response_json}"
        siemplify.result.add_result_json(response_json)
    except Exception as e:
        output_message = f"Error executing {siemplify.script_name}. Reason {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.end(output_message, result_value, status)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )


if __name__ == "__main__":
    main()
