from __future__ import annotations

from typing import TYPE_CHECKING

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import ASSIGN_TO_GROUP_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import JamfError
from ..core.JamfManager import JamfManager

if TYPE_CHECKING:
    from typing import NoReturn


@output_handler
def main() -> NoReturn:
    """
    Assign computers to a specific computer group in Jamf Pro.

    This action adds computers to a computer group using various identifiers:
    computer IDs, computer names, or serial numbers. At least one type of
    identifier must be provided. Supports bulk operations with comma-separated
    lists of identifiers.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = ASSIGN_TO_GROUP_SCRIPT_NAME
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
        group_id = extract_action_param(
            siemplify,
            param_name="Group ID",
            is_mandatory=True,
            print_value=True,
        )
        computer_ids = extract_action_param(
            siemplify,
            param_name="Computer IDs",
            is_mandatory=False,
            print_value=True,
            default_value="",
        )
        computer_names = extract_action_param(
            siemplify,
            param_name="Computer Names",
            is_mandatory=False,
            print_value=True,
            default_value="",
        )
        computer_serial_numbers = extract_action_param(
            siemplify,
            param_name="Computer Serial Numbers",
            is_mandatory=False,
            print_value=True,
            default_value="",
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        # Validate input parameters
        if not computer_ids and not computer_names and not computer_serial_numbers:
            raise Exception(
                "At least one computer identifier (Computer IDs, Computer Names, "
                "or Computer Serial Numbers) must be provided"
            )

        # Parse comma-separated lists
        computer_ids_list = []
        computer_names_list = []
        computer_serial_numbers_list = []

        if computer_ids and computer_ids.strip():
            computer_ids_list = [id.strip() for id in computer_ids.split(",") if id.strip()]

        if computer_names and computer_names.strip():
            computer_names_list = [
                name.strip() for name in computer_names.split(",") if name.strip()
            ]

        if computer_serial_numbers and computer_serial_numbers.strip():
            computer_serial_numbers_list = [
                serial.strip() for serial in computer_serial_numbers.split(",") if serial.strip()
            ]

        # Validate that at least one list has items
        total_computers = (
            len(computer_ids_list) + len(computer_names_list) + len(computer_serial_numbers_list)
        )
        if total_computers == 0:
            raise Exception("No valid computer identifiers provided")

        siemplify.LOGGER.info(f"Starting Assign to Group action - Group ID: {group_id}")
        siemplify.LOGGER.info(
            f"Computer IDs: {len(computer_ids_list)}, Names: {len(computer_names_list)}, "
            f"Serials: {len(computer_serial_numbers_list)}"
        )

        # Initialize Jamf Manager
        jamf_manager = JamfManager(
            api_root=api_root,
            client_api_id=client_api_id,
            client_api_secret=client_api_secret,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        # Assign computers to group
        result = jamf_manager.assign_to_group(
            group_id=group_id,
            computer_ids=computer_ids_list if computer_ids_list else None,
            computer_names=computer_names_list if computer_names_list else None,
            computer_serial_numbers=computer_serial_numbers_list
            if computer_serial_numbers_list
            else None,
        )

        siemplify.LOGGER.info(f"Result in Assign to Group action - Group ID: {result}")
        # Process results
        computers_processed = result.get("computers_processed", total_computers)
        group_name = result.get("group_name", f"Group {group_id}")

        # Create output message
        output_message = f"Successfully added {computers_processed} computer(s) to {group_name}"

        # Add details
        details = []
        if computer_ids_list:
            details.append(f"{len(computer_ids_list)} computer ID(s)")
        if computer_names_list:
            details.append(f"{len(computer_names_list)} computer name(s)")
        if computer_serial_numbers_list:
            details.append(f"{len(computer_serial_numbers_list)} serial number(s)")

        if details:
            output_message += f"\n\nProcessed: {', '.join(details)}"

        # Add computer details to output (first few items)
        computer_details = []
        if computer_ids_list:
            computer_details.extend([f"ID: {id}" for id in computer_ids_list[:3]])
        if computer_names_list:
            computer_details.extend([f"Name: {name}" for name in computer_names_list[:3]])
        if computer_serial_numbers_list:
            computer_details.extend([
                f"Serial: {serial}" for serial in computer_serial_numbers_list[:3]
            ])

        if computer_details:
            output_message += "\n\nComputer Details:\n• " + "\n• ".join(computer_details)
            if total_computers > 3:
                output_message += f"\n... and {total_computers - 3} more computer(s)"

        # Set JSON result
        siemplify.result.add_result_json(result)

        siemplify.LOGGER.info("Successfully completed Assign to Group action")
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except JamfError as e:
        siemplify.LOGGER.error(f"Jamf API error while assigning computers to group: {e}")
        siemplify.LOGGER.exception(e)
        output_message = f"Jamf API error: {str(e)}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        siemplify.LOGGER.error(f"Unexpected error while assigning computers to group: {e}")
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
