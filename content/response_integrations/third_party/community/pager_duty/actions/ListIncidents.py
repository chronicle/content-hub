from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SCRIPT_NAME_LISTINCIDENTS
from ..core.PagerDutyManager import PagerDutyManager


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INTEGRATION_NAME + SCRIPT_NAME_LISTINCIDENTS
    configurations = siemplify.get_configuration(INTEGRATION_NAME)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_token = configurations["api_key"]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    pager_duty = PagerDutyManager(api_token)
    try:
        siemplify.LOGGER.info("Getting all the incidents")
        incidents = pager_duty.get_all_incidents()
        output_message = "Incidents not found\n"
        siemplify.result.add_result_json(incidents)
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        
        if incidents:
            output_message = "Successfully retrieved Incidents\n"

    except Exception as e:
        output_message = f"There was an error to retrieve all incidents.{e!s}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
