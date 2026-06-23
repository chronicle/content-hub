from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction

from constants import INTEGRATION_NAME, SCRIPT_NAME_LISTUSERS
from PagerDutyManager import PagerDutyManager
import json


def main():
    siemplify = SiemplifyAction()
    json_result = {}
    siemplify.script_name = INTEGRATION_NAME + "Send Event"
    configurations = siemplify.get_configuration(INTEGRATION_NAME)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    routing_key = siemplify.parameters["Routing Key"]
    payload = json.loads(siemplify.parameters["Payload"])

    payload['routing_key'] = routing_key

    siemplify.LOGGER.info("----------------- Main - Start -----------------")
    pager_duty = PagerDutyManager(None)

    try:
        siemplify.LOGGER.info("Started sending an event to PagerDuty")
        event_response = pager_duty.send_event(payload)

        json_result = event_response
        output_message = "Successfully Created Event\n"
        result_value = "true"
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f"There was an error creating a new incident.{e!s}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.result.add_result_json(json_result)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
