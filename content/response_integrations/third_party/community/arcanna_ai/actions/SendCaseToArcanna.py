from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.arcanna_client import ArcannaClient
from ..core.constants import SEND_CASE_SCRIPT_NAME
from ..core.utils import fetch_field_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEND_CASE_SCRIPT_NAME
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
    event_id_field = siemplify.extract_action_param(
        "Case identifier field",
        print_value=True,
        is_mandatory=False,
    )
    to_use_existing_id = str(
        siemplify.extract_action_param(
            "Use case ID as ID in Arcanna",
            print_value=True,
            is_mandatory=True,
        ),
    ).lower()

    full_case = siemplify._get_case()

    status = EXECUTION_STATE_COMPLETED
    output_message = f"{siemplify.script_name}: "
    result_value = None

    if full_case is None:
        status = EXECUTION_STATE_FAILED
        output_message += "No case details returned"
        result_value = False
        siemplify.end(output_message, result_value, status)

    try:
        client = ArcannaClient(api_key=api_key, base_url=arcanna_url, verify=ssl_verify)

        event_id = None
        if to_use_existing_id == "true":
            event_id = fetch_field_value(full_case, event_id_field)

        raw_payload = full_case
        title = full_case.get("title")
        target_entities = siemplify.context_data.get("target_entities")
        raw_payload["target_entities"] = target_entities
        response_json = client.send_raw_event(
            job_id=job_id,
            raw_body=raw_payload,
            event_id=event_id,
        )
        result_value = True
        output_message = (
            output_message + f"response={json.dumps(response_json, indent=2)}"
        )
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
