from __future__ import annotations

from ..core.NetskopeManagerFactory import NetskopeManagerFactory
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME: str = "Netskope"
SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Deploy URL List Changes"


@output_handler
def main() -> None:
    """
    Deploy pending URL list changes to the active Netskope policy engine.
    """
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    result_value = False

    try:
        manager = NetskopeManagerFactory.get_manager(siemplify, api_version="v2")

        siemplify.LOGGER.info("Starting to perform the action")
        manager.deploy_url_list_changes()
        siemplify.LOGGER.info("Finished performing the action")
        output_message = "Successfully deployed pending Netskope policy changes."
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:  # pylint: disable=broad-exception-caught
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
