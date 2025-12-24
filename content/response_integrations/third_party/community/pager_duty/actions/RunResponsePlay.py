from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SCRIPT_NAME_RUN_RESPONSE
from ..core.PagerDutyManager import PagerDutyManager


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INTEGRATION_NAME + SCRIPT_NAME_RUN_RESPONSE
    configurations = siemplify.get_configuration(INTEGRATION_NAME)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_token = configurations["api_key"]
    user_email = siemplify.extract_action_param("Email").strip()
    response_plays_id = siemplify.extract_action_param("Response ID").strip()
    user_id = siemplify.extract_action_param("Incident_ID")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    pager_duty = PagerDutyManager(api_token)

    try:
        siemplify.LOGGER.info("Starting the incident response ")

        response_play = pager_duty.run_response_play(
            user_email,
            response_plays_id,
            user_id,
        )
        siemplify.result.add_result_json(response_play)
        output_message = "The response was Successfully runed "
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f"There is no response in the incident .{e!s}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
