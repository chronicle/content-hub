from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import ApiManager
from ..core.rrs_exceptions import RrsException


@output_handler
def main() -> None:
    """Bring a storage volume online via the Ransomware Resilience Service.

    Calls the RRS API to bring the target volume online and reports the result
    back to the SOAR platform.
    """
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Volume Online: Init -----------------")

    volume_online_result = None
    try:
        rrsManager = ApiManager(siemplify)
        # Extract parameters from action
        volume_id = siemplify.extract_action_param("Volume ID", is_mandatory=True, print_value=True)
        agent_id = siemplify.extract_action_param("Agent ID", is_mandatory=True, print_value=True)
        system_id = siemplify.extract_action_param("System ID", is_mandatory=True, print_value=True)
        siemplify.LOGGER.info("----------------- RRS - Volume Online: Started -----------------")

        # call volume online api
        volume_online_result = rrsManager.volume_online(volume_id, agent_id, system_id)
        # used to flag back to siemplify system, the action final status
        status = EXECUTION_STATE_COMPLETED
        # human readable message, showed in UI as the action result
        output_message = (
            "Successfully brought volume online on the following entities using NetApp Ransomware Resilience: "
            f"{volume_id}"
        )
        # Set a simple result value, used for playbook if\else and placeholders.
        result_value = True

    except RrsException as e:
        output_message = f'Error executing action "Volume Online". Reason: {e}'
        siemplify.LOGGER.error(f"Volume Online: RRS error - {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        volume_online_result = {}

    except Exception as e:
        output_message = f'Error executing action "Volume Online". Reason: {e}'
        siemplify.LOGGER.error(f"Volume Online: Failed to bring volume online. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        volume_online_result = {}

    siemplify.LOGGER.info("----------------- RRS - Volume Online: End -----------------")
    siemplify.LOGGER.info(
        f"Volume Online: \n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )

    # Add result to action output.
    siemplify.result.add_result_json(volume_online_result)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
