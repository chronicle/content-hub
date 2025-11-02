from __future__ import annotations

from typing import TYPE_CHECKING

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import GET_DEVICE_GROUP_MEMBERSHIP_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import JamfError, JamfManagerError
from ..core.JamfManager import JamfManager

if TYPE_CHECKING:
    from typing import NoReturn


@output_handler
def main() -> NoReturn:
    """
    Retrieve membership information for a specific device group from Jamf Pro.

    This action fetches detailed membership information for a computer group,
    including all member devices and their basic information. Works with both
    static and smart computer groups.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_DEVICE_GROUP_MEMBERSHIP_SCRIPT_NAME
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
            is_mandatory=False,
            default_value=True,
            print_value=True,
        )

        # Action parameters
        group_id = extract_action_param(
            siemplify,
            param_name="Group ID",
            is_mandatory=True,
            print_value=True,
        )

        siemplify.LOGGER.info(
            f"Starting Get Device Group Membership action for group ID: {group_id}"
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

        # Retrieve device group membership
        membership_data = jamf_manager.get_device_group_membership(group_id)

        if membership_data:
            siemplify.LOGGER.info(
                f"Successfully retrieved device group membership for ID: {group_id}"
            )

            # Extract member information
            members = membership_data.get("computer_group", {}).get("computers", [])
            member_count = len(members)

            # Prepare comprehensive result
            json_result = {
                "group_id": group_id,
                "member_count": member_count,
                "membership_data": membership_data,
            }

            siemplify.result.add_result_json(json_result)

            output_message = (
                f"Successfully retrieved device group membership for group ID {group_id}. "
                f"Found {member_count} members"
            )
            result_value = True
            status = EXECUTION_STATE_COMPLETED

        else:
            siemplify.LOGGER.info(f"No membership data found for device group ID: {group_id}")
            output_message = f"No membership data found for device group ID: {group_id}"
            result_value = False
            status = EXECUTION_STATE_COMPLETED

    except JamfError as e:
        siemplify.LOGGER.error(f"Jamf API error while retrieving device group membership: {e}")
        siemplify.LOGGER.exception(e)
        output_message = f"Jamf API error: {str(e)}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    except JamfManagerError as e:
        siemplify.LOGGER.error(f"Jamf Manager error while retrieving device group membership: {e}")
        siemplify.LOGGER.exception(e)
        output_message = f"Jamf Manager error: {str(e)}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        siemplify.LOGGER.error(f"Unexpected error while retrieving device group membership: {e}")
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
