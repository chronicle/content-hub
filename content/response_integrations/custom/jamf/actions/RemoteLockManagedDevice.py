from __future__ import annotations

from typing import TYPE_CHECKING

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler, unix_now
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import INTEGRATION_NAME, REMOTE_LOCK_MANAGED_DEVICE_SCRIPT_NAME
from ..core.exceptions import JamfError
from ..core.JamfManager import JamfManager

if TYPE_CHECKING:
    from typing import NoReturn


@output_handler
def main() -> NoReturn:
    """
    Remotely lock a managed computer using Jamf Pro MDM command.

    This action sends a device_lock MDM command to remotely lock a managed device
    with optional custom message and phone number display.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOTE_LOCK_MANAGED_DEVICE_SCRIPT_NAME
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

        # EXTRACT ACTION PARAMETERS:
        computer_id = extract_action_param(
            siemplify,
            param_name="Computer ID",
            is_mandatory=True,
            print_value=True,
        )
        pin = extract_action_param(
            siemplify,
            param_name="PIN",
            is_mandatory=True,
            print_value=False,
        )
        message = extract_action_param(
            siemplify,
            param_name="Message",
            is_mandatory=False,
            print_value=True,
        )
        phone_number = extract_action_param(
            siemplify,
            param_name="Phone Number",
            is_mandatory=False,
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

        siemplify.LOGGER.info(f"Attempting to remotely lock computer with ID: {computer_id}")

        # Execute the remote lock command
        result = jamf_manager.remote_lock_device(
            computer_id=computer_id,
            pin=pin,
            message=message,
            phone_number=phone_number,
        )

        # Prepare result
        command_details = {
            "computer_id": computer_id,
            "command_type": "device_lock",
            "message_used": bool(message),
            "phone_number_used": bool(phone_number),
            "pin_used": bool(pin),
            "timestamp": unix_now(),
            "status": "initiated",
        }

        json_result = {"lock_command_result": result, "command_details": command_details}

        siemplify.result.add_result_json(json_result)

        # Create output message
        output_message = (
            f"Successfully initiated remote lock command for computer ID: {computer_id}"
        )

        details = []
        if message:
            details.append("with custom message")
        if phone_number:
            details.append("with phone number display")

        if details:
            output_message += f" ({', '.join(details)})"

        result_value = True

    except JamfError as e:
        siemplify.LOGGER.error(f"Jamf API error while locking device: {e}")
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
