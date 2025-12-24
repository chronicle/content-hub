from __future__ import annotations

from typing import TYPE_CHECKING

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler, unix_now
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import INTEGRATION_NAME, WIPE_MANAGED_DEVICE_SCRIPT_NAME
from ..core.exceptions import JamfError
from ..core.JamfManager import JamfManager

if TYPE_CHECKING:
    from typing import NoReturn


@output_handler
def main() -> NoReturn:
    """
    Wipe/erase a managed computer remotely using Jamf Pro ERASE_DEVICE MDM command.

    This action sends an ERASE_DEVICE MDM command to completely wipe a managed device.
    The action supports various options including obliteration behavior, return to service
    settings, and device setup preferences.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = WIPE_MANAGED_DEVICE_SCRIPT_NAME
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
        obliteration_behavior = extract_action_param(
            siemplify,
            param_name="Obliteration Behavior",
            is_mandatory=True,
            print_value=True,
            default_value="Default",
        )
        return_to_service = extract_action_param(
            siemplify,
            param_name="Return to Service",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
            default_value=True,
        )
        mdm_profile_data = extract_action_param(
            siemplify,
            param_name="MDM Profile Data",
            is_mandatory=False,
            print_value=False,
        )
        wifi_profile_data = extract_action_param(
            siemplify,
            param_name="WiFi Profile Data",
            is_mandatory=False,
            print_value=False,
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

        siemplify.LOGGER.info(f"Attempting to erase computer with ID: {computer_id}")

        # Execute the erase command
        result = jamf_manager.erase_computer(
            computer_id=computer_id,
            pin=pin,
            obliteration_behavior=obliteration_behavior,
            return_to_service=return_to_service,
            mdm_profile_data=mdm_profile_data,
            wifi_profile_data=wifi_profile_data,
        )

        # Prepare result
        command_details = {
            "computer_id": computer_id,
            "command_type": "ERASE_DEVICE",
            "obliteration_behavior": obliteration_behavior,
            "return_to_service": return_to_service,
            "pin_used": bool(pin),
            "mdm_profile_provided": bool(mdm_profile_data),
            "wifi_profile_provided": bool(wifi_profile_data),
            "timestamp": unix_now(),
            "status": "initiated",
        }

        json_result = {"erase_command_result": result, "command_details": command_details}

        siemplify.result.add_result_json(json_result)

        # Create output message
        output_message = (
            f"Successfully initiated ERASE_DEVICE command for computer ID: {computer_id}"
        )

        # Add parameter details to output message
        details = []
        if pin:
            details.append("with PIN protection")
        if obliteration_behavior != "Default":
            details.append(f"obliteration: {obliteration_behavior}")
        if return_to_service:
            details.append("return to service")

        if details:
            output_message += f" ({', '.join(details)})"

        result_value = True

    except JamfError as e:
        siemplify.LOGGER.error(f"Jamf API error while erasing computer: {e}")
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
