from __future__ import annotations

from typing import TYPE_CHECKING

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import INTEGRATION_NAME, UPDATE_EXTENSION_ATTRIBUTE_SCRIPT_NAME
from ..core.exceptions import JamfError
from ..core.JamfManager import JamfManager

if TYPE_CHECKING:
    from typing import NoReturn


@output_handler
def main() -> NoReturn:
    """
    Update extension attributes for a specific computer in Jamf Pro.

    This action updates extension attribute values for a computer by first
    fetching available extension attributes from Jamf Pro, finding the
    specified attribute by name, and then updating it with the provided
    values. Supports multiple values as a comma-separated list.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_EXTENSION_ATTRIBUTE_SCRIPT_NAME
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
            is_mandatory=False,
            input_type=bool,
            print_value=True,
            default_value=True,
        )

        # Action parameters
        computer_id = extract_action_param(
            siemplify,
            param_name="Computer ID",
            is_mandatory=True,
            print_value=True,
        )
        extension_attribute_name = extract_action_param(
            siemplify,
            param_name="Extension Attribute Name",
            is_mandatory=True,
            print_value=True,
        )
        values = extract_action_param(
            siemplify,
            param_name="Values",
            is_mandatory=True,
            print_value=True,
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        # Parse values from comma-separated string
        values_list = []
        if values and values.strip():
            values_list = [value.strip() for value in values.split(",") if value.strip()]

        if not values_list:
            raise Exception("At least one value must be provided")

        # Create JamfManager instance
        jamf_manager = JamfManager(
            api_root=api_root,
            client_api_id=client_api_id,
            client_api_secret=client_api_secret,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        # First, get all extension attributes to populate the dropdown
        siemplify.LOGGER.info("Fetching extension attributes for dropdown population")
        extension_attributes_list = jamf_manager.list_computer_extension_attributes()

        # Extract attribute names for dropdown options
        # attribute_names = [attr["name"] for attr in extension_attributes_list]

        siemplify.LOGGER.info(f"Selected extension attribute: {extension_attribute_name}")

        # Find the extension attribute by name
        selected_attribute = None
        for attr in extension_attributes_list:
            if attr["name"].lower() == extension_attribute_name.lower():
                selected_attribute = attr
                break

        if not selected_attribute:
            available_names = [attr["name"] for attr in extension_attributes_list]
            raise Exception(
                f"Extension attribute '{extension_attribute_name}' not found. "
                f"Available attributes: {', '.join(available_names)}"
            )

        definition_id = selected_attribute["id"]
        siemplify.LOGGER.info(
            f"Found extension attribute '{extension_attribute_name}' with ID: {definition_id}"
        )

        # Create extension attribute structure for the API call (support multiple values)
        extension_attribute = {"definitionId": definition_id, "values": values_list}

        siemplify.LOGGER.info(
            f"Starting Update Extension Attributes action - Computer ID: {computer_id}"
        )
        siemplify.LOGGER.info(
            f"Extension Attribute: {extension_attribute_name} (ID: {definition_id}), "
            f"Values: {', '.join(values_list)}"
        )

        # Update extension attributes
        result = jamf_manager.update_computer_extension_attribute(
            computer_id=computer_id, extension_attribute=extension_attribute
        )

        # Process results
        computer_name = result.get("general", {}).get("name", f"Computer {computer_id}")

        # Create output message
        values_display = ", ".join(values_list[:3])  # Show first 3 values
        if len(values_list) > 3:
            values_display += f" (and {len(values_list) - 3} more)"

        output_message = (
            f"Successfully updated extension attribute (Definition ID: {definition_id}) "
            f"for {computer_name}"
        )
        output_message += f"\n\nValues Set: {values_display}"

        # Add computer details to output
        if result.get("general"):
            general = result["general"]
            computer_details = []
            if general.get("name"):
                computer_details.append(f"Name: {general['name']}")
            if general.get("serialNumber"):
                computer_details.append(f"Serial: {general['serialNumber']}")
            if general.get("platform"):
                computer_details.append(f"Platform: {general['platform']}")

            if computer_details:
                output_message += "\n\nComputer Details:\n• " + "\n• ".join(computer_details)

        # Set JSON result
        siemplify.result.add_result_json(result)

        # Set execution state
        siemplify.LOGGER.info("Successfully completed Update Extension Attributes action")
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except JamfError as e:
        siemplify.LOGGER.error(f"Jamf API error while updating extension attributes: {e}")
        siemplify.LOGGER.exception(e)
        output_message = f"Jamf API error: {str(e)}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        siemplify.LOGGER.error(f"Unexpected error while updating extension attributes: {e}")
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
