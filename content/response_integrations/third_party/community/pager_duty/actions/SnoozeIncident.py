from __future__ import annotations

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SCRIPT_NAME_SNOOZE
from ..core.PagerDutyManager import PagerDutyManager


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INTEGRATION_NAME + SCRIPT_NAME_SNOOZE
    configurations = siemplify.get_configuration(INTEGRATION_NAME)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_token = configurations["api_key"]
    email_from = siemplify.extract_action_param("Email")
    incident_id = siemplify.extract_action_param("IncidentID")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    pager_duty = PagerDutyManager(api_token)
    try:
        siemplify.LOGGER.info("Starting Snoozing process")
        incident = pager_duty.snooze_incident(email_from, incident_id)
        siemplify.result.add_result_json(incident)
        output_message = "Successfully Snoozed Incident\n"
        result_value = True
        status = EXECUTION_STATE_COMPLETED
    except requests.HTTPError as e:
        output_message = (
            f"Incident wasnt snoozed\nPagerDuty API error: {e.response.status_code} "
            f"{e.response.reason}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
