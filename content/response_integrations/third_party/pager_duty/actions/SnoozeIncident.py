from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SCRIPT_NAME_LISTUSERS
from ..core.Exceptions import PagerDutyException
from ..core.PagerDutyManager import PagerDutyManager


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INTEGRATION_NAME + SCRIPT_NAME_LISTUSERS
    configurations = siemplify.get_configuration(INTEGRATION_NAME)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_token = configurations["api_key"]
    email_from = siemplify.parameters["Email"]
    incident_id = siemplify.parameters["IncidentID"]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    pager_duty = PagerDutyManager(api_token)
    try:
        siemplify.LOGGER.info("Starting Snoozing process")
        try:
            incident = pager_duty.snooze_incident(email_from, incident_id)
            result_value = True
            status = EXECUTION_STATE_COMPLETED
            siemplify.result.add_result_json(incident)
            output_message = "Incident wasnt snoozed\n"
            if incident:
                output_message = "Successfully Snoozed Incident\n"

        except PagerDutyException as e:
            output_message = f"Incident wasnt snoozed\n {e!s}"
            result_value = False
            status = EXECUTION_STATE_FAILED

    except Exception as e:
        output_message = f"There was a problem finding and snoozing the incident. {e!s}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
