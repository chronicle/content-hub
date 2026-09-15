from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SCRIPT_NAME_LISTUSERS
from ..core.PagerDutyManager import PagerDutyManager


def main():
    siemplify = SiemplifyAction()
    json_result = {}
    siemplify.script_name = INTEGRATION_NAME + SCRIPT_NAME_LISTUSERS
    configurations = siemplify.get_configuration(INTEGRATION_NAME)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_token = configurations["api_key"]
    service = configurations["Services"]
    title = siemplify.parameters["Title"]
    email_from = siemplify.parameters["Email"]
    urgency = siemplify.parameters["Urgency"]
    body = siemplify.parameters["Details"]

    siemplify.LOGGER.info("----------------- Main - Start -----------------")
    pager_duty = PagerDutyManager(api_token)

    try:
        siemplify.LOGGER.info("Started Creating a new incident")
        incident = pager_duty.create_incident(email_from, title, service, urgency, body)

        json_result = incident
        output_message = "Successfully Created Incident\n"
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
