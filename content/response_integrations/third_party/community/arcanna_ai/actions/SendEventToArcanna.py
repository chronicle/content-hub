from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.arcanna_client import ArcannaClient
from ..core.constants import SEND_CASE_SCRIPT_NAME


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

    job_id = int(
        siemplify.extract_action_param("Job ID", print_value=True, is_mandatory=True),
    )
    username = siemplify.extract_action_param(
        "Username",
        print_value=True,
        is_mandatory=True,
    )
    event_id_field = siemplify.extract_action_param(
        "Event ID mapping field",
        print_value=True,
        is_mandatory=False,
    )
    send_individual_alerts = siemplify.extract_action_param(
        "Send individual alerts from case",
        print_value=True,
        is_mandatory=True,
    )

    full_case = siemplify._get_case()

    status = EXECUTION_STATE_COMPLETED
    output_message = "output message :"
    result_value = None

    if full_case is None:
        status = EXECUTION_STATE_FAILED
        output_message = "No case details returned"
        result_value = False
        siemplify.end(output_message, result_value, status)

    try:
        client = ArcannaClient(
            api_key=api_key,
            base_url=arcanna_url,
            verify=False,
        )
        severity = 0
        if send_individual_alerts == "true":
            response_json = {}
            json_response = []

            cyber_alerts = full_case.get("cyber_alerts", [])
            current_alert = siemplify.current_alert

            siemplify.LOGGER.info(current_alert.identifier)
            current_alert_identifier = current_alert.identifier
            for alert in cyber_alerts:
                event_id = None
                raw_payload = alert
                title = alert.get("identifier")
                if title != current_alert_identifier:
                    output_message += (
                        f"Skipping {title} because {current_alert_identifier} "
                    )
                    continue
                output_message += f"  Adding {title} as it was found "
                if event_id_field:
                    event_id_field = event_id_field.split(".")
                    event_id = alert
                    for tok in event_id_field:
                        event_id = event_id.get(tok)
                raw_payload["siemplify_username"] = username
                response_json = client.send_raw_event(
                    job_id=job_id,
                    raw_body=raw_payload,
                    event_id=event_id,
                )
                rresult_value = True
                output_message = (
                    output_message + f"response={json.dumps(response_json, indent=2)}"
                )
                json_response.append(response_json)
            siemplify.result.add_result_json(response_json)
        else:
            event_id = None
            if event_id_field:
                event_id_field = event_id_field.split(".")
                event_id = full_case
                for tok in event_id_field:
                    event_id = event_id.get(tok)
            raw_payload = full_case
            title = full_case.get("title")
            target_entities = siemplify.context_data.get("target_entities")
            raw_payload["siemplify_username"] = username
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
        output_message = f"Error executing {SEND_CASE_SCRIPT_NAME}. Reason {e}"
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
