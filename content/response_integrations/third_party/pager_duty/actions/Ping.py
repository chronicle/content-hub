from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SCRIPT_NAME_PING
from ..core.PagerDutyManager import PagerDutyManager


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME}{SCRIPT_NAME_PING}"

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    configurations = siemplify.get_configuration(INTEGRATION_NAME)
    api_token = configurations["api_key"]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        pager_duty = PagerDutyManager(api_token)
        pager_duty.test_connectivity()
        output_message = "Successfully connected to the PagerDuty API."
        result_value = True
        status = EXECUTION_STATE_COMPLETED
    except Exception as e:
        output_message = f"Failed to connect to the PagerDuty API. Error: {e}"
        result_value = False
        status = EXECUTION_STATE_FAILED
    
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
