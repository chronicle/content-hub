from __future__ import annotations

from typing import TYPE_CHECKING

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import GET_DEVICE_INFORMATION_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import JamfError, JamfManagerError
from ..core.JamfManager import JamfManager

if TYPE_CHECKING:
    from typing import NoReturn


@output_handler
def main() -> NoReturn:
    """
    Retrieve detailed information for a specific device from Jamf Pro.

    This action fetches comprehensive device information including general details,
    hardware specifications, operating system information, and user/location data
    for a specified device ID from Jamf Pro.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_DEVICE_INFORMATION_SCRIPT_NAME
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
            print_value=False,
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

        # Action parameters
        computer_id = extract_action_param(
            siemplify,
            param_name="Computer ID",
            is_mandatory=True,
            print_value=True,
        )

        siemplify.LOGGER.info(
            f"Starting Get Device Information action for device ID: {computer_id}"
        )
        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        # Initialize Jamf Manager
        jamf_manager = JamfManager(
            api_root=api_root,
            client_api_id=client_api_id,
            client_api_secret=client_api_secret,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        # Retrieve device information
        device_info = jamf_manager.get_device_info(computer_id)

        if device_info:
            siemplify.LOGGER.info(
                f"Successfully retrieved device information for ID: {computer_id}"
            )

            # Prepare comprehensive result
            json_result = {
                "device_id": computer_id,
                "device_info": device_info,
            }

            siemplify.result.add_result_json(json_result)

            output_message = f"Successfully retrieved device information for (ID: {computer_id})"
            result_value = True
            status = EXECUTION_STATE_COMPLETED

        else:
            siemplify.LOGGER.info(f"No device information found for ID: {computer_id}")
            output_message = f"No device information found for device ID: {computer_id}"
            result_value = False
            status = EXECUTION_STATE_COMPLETED

    except JamfError as e:
        siemplify.LOGGER.error(f"Jamf API error in Get Device Information action: {str(e)}")
        output_message = f"Jamf API error: {str(e)}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    except JamfManagerError as e:
        siemplify.LOGGER.error(f"Jamf Manager error in Get Device Information action: {str(e)}")
        output_message = f"Jamf Manager error: {str(e)}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        siemplify.LOGGER.error(f"Unexpected error in Get Device Information action: {str(e)}")
        siemplify.LOGGER.exception(e)
        output_message = f"Unexpected error: {str(e)}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
