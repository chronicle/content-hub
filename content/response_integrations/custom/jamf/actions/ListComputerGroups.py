from __future__ import annotations

from typing import TYPE_CHECKING

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param

from ..core.constants import INTEGRATION_NAME, LIST_COMPUTER_GROUPS_SCRIPT_NAME
from ..core.exceptions import JamfError
from ..core.JamfManager import JamfManager

if TYPE_CHECKING:
    from typing import NoReturn


@output_handler
def main() -> NoReturn:
    """
    List all computer groups from Jamf Pro.

    This action retrieves all computer groups configured in Jamf Pro,
    including both static and smart groups, and returns them as JSON.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_COMPUTER_GROUPS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = False

    try:
        # INIT INTEGRATION CONFIGURATION:
        api_root = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Jamf Pro API Root",
            is_mandatory=True,
            print_value=True,
        )
        client_api_id = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Jamf Pro Client API ID",
            is_mandatory=True,
            print_value=True,
        )
        client_api_secret = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Jamf Pro Client API Secret",
            is_mandatory=True,
            print_value=False,
        )
        verify_ssl = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            is_mandatory=True,
            default_value=True,
            print_value=True,
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        # Create JamfManager instance
        jamf_manager = JamfManager(
            api_root=api_root,
            client_api_id=client_api_id,
            client_api_secret=client_api_secret,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info("Attempting to retrieve computer groups from Jamf Pro")

        # Retrieve computer groups
        computer_groups = jamf_manager.list_computer_groups()

        if computer_groups:
            # Prepare result
            json_result = {"computer_groups": computer_groups}

            siemplify.result.add_result_json(json_result)
            output_message = (
                f"Successfully retrieved {len(computer_groups)} computer groups from Jamf Pro"
            )
            result_value = True

        else:
            siemplify.LOGGER.info("No computer groups found")
            json_result = {"computer_groups": []}
            siemplify.result.add_result_json(json_result)
            output_message = "No computer groups found in Jamf Pro"
            result_value = True  # Still successful, just empty results

    except JamfError as e:
        siemplify.LOGGER.error(f"Jamf API error while listing computer groups: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message = f"Jamf API error: {e}"
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
