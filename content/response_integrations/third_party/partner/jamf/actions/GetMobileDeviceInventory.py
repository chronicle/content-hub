from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import (
    GET_MOBILE_DEVICE_INVENTORY_SCRIPT_NAME,
    INTEGRATION_NAME,
    MOBILE_DEVICE_ALL_SECTIONS,
)
from ..core.exceptions import JamfError
from ..core.JamfManager import JamfManager

if TYPE_CHECKING:
    from typing import NoReturn


@output_handler
def main() -> NoReturn:
    """
    Retrieve mobile device inventory from Jamf Pro with pagination and filtering support.

    This action retrieves mobile device inventory data from Jamf Pro using the v2 API
    with support for pagination, sorting, and filtering to optimize data retrieval.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_MOBILE_DEVICE_INVENTORY_SCRIPT_NAME
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
        page = extract_action_param(
            siemplify,
            param_name="Page",
            is_mandatory=False,
            print_value=True,
            default_value="0",
        )
        page_size = extract_action_param(
            siemplify,
            param_name="Page Size",
            is_mandatory=False,
            print_value=True,
            default_value="100",
        )
        sort_criteria = extract_action_param(
            siemplify,
            param_name="Sort",
            is_mandatory=False,
            print_value=True,
            default_value="",
        )
        filter_field = extract_action_param(
            siemplify,
            param_name="Filter",
            is_mandatory=False,
            print_value=True,
            default_value="",
        )
        filter_value = extract_action_param(
            siemplify,
            param_name="Filter Value",
            is_mandatory=False,
            print_value=True,
            default_value="",
        )
        sections = extract_action_param(
            siemplify,
            param_name="Section",
            is_mandatory=False,
            print_value=True,
            default_value="ALL",
        )

        # Convert and validate parameters
        try:
            page = int(page)
            page_size = int(page_size)
        except ValueError:
            raise JamfError("Page and Page Size must be valid integers")

        if page < 0:
            raise JamfError("Page number must be 0 or greater")
        if page_size < 1:
            raise JamfError("Page size must be greater than 0")

        # Convert list parameters to API-compatible strings
        sort_string = None
        if sort_criteria and isinstance(sort_criteria, list) and len(sort_criteria) > 0:
            sort_string = ",".join([str(item) for item in sort_criteria if item])
            siemplify.LOGGER.info(f"Sort criteria converted: {sort_string}")
        elif sort_criteria and isinstance(sort_criteria, str) and sort_criteria.strip():
            stripped_sort = sort_criteria.strip()
            if stripped_sort in ["[]", "[null]", "null", ""]:
                sort_string = None
            else:
                try:
                    parsed_sort = json.loads(stripped_sort)
                    if isinstance(parsed_sort, list) and len(parsed_sort) > 0:
                        sort_string = ",".join([str(item) for item in parsed_sort if item])
                    else:
                        sort_string = None
                except (json.JSONDecodeError, ValueError):
                    sort_string = stripped_sort
            siemplify.LOGGER.info(f"Sort criteria processed: {sort_string}")

        # Build filter string from field and value
        filter_string = None
        if filter_field and filter_field.strip() and filter_value and filter_value.strip():
            filter_string = f'{filter_field.strip()}=="{filter_value.strip()}"'
            siemplify.LOGGER.info(f"Filter applied: {filter_string}")

        def get_section_for_filter_field(field):
            """
            Determine the appropriate section based on the filter field.

            Args:
                field (str): The filter field name

            Returns:
                str: The corresponding section name in uppercase
            """
            if not field:
                return "GENERAL"  # Default fallback

            field = field.strip().lower()

            # Handle special cases for mobile devices
            if field == "udid" or field == "serialnumber":
                return "HARDWARE"
            elif field == "username" or field == "emailaddress":
                return "USER_AND_LOCATION"
            else:
                # Default to GENERAL for mobile device fields
                return "GENERAL"

        # Process sections parameter (handle both string and list formats)
        sections_list = []
        all_sections_requested = False
        if sections:
            if isinstance(sections, list):
                # Check if ALL is in the list and filter out "ALL" from final list
                if any(section.strip().upper() == "ALL" for section in sections if section):
                    all_sections_requested = True
                    sections_list = MOBILE_DEVICE_ALL_SECTIONS.copy()
                else:
                    sections_list = [
                        section.strip().upper()
                        for section in sections
                        if section and section.strip() and section.strip().upper() != "ALL"
                    ]
            elif isinstance(sections, str):
                # Handle comma-separated string or single value
                sections_str = sections.strip()
                if sections_str:
                    # Handle "ALL" option - include all available sections
                    if sections_str.upper() == "ALL" or "ALL" in sections_str.upper():
                        all_sections_requested = True
                        sections_list = MOBILE_DEVICE_ALL_SECTIONS.copy()
                    else:
                        # Try to parse as JSON array first
                        try:
                            parsed_sections = json.loads(sections_str)
                            if isinstance(parsed_sections, list):
                                sections_list = [
                                    section.strip().upper()
                                    for section in parsed_sections
                                    if section and section.strip()
                                ]
                            else:
                                sections_list = [sections_str.upper()]
                        except (json.JSONDecodeError, ValueError):
                            # Treat as comma-separated string or single value
                            if "," in sections_str:
                                sections_list = [
                                    section.strip().upper()
                                    for section in sections_str.split(",")
                                    if section.strip()
                                ]
                            else:
                                sections_list = [sections_str.upper()]

        # Ensure we have at least one section
        if not sections_list:
            sections_list = ["GENERAL"]

        # Auto-determine required section based on filter field and ensure it's included
        if filter_field and filter_field.strip() and not all_sections_requested:
            required_section = get_section_for_filter_field(filter_field)
            if required_section not in sections_list:
                sections_list.append(required_section)
                siemplify.LOGGER.info(
                    f"Auto-added required section '{required_section}' "
                    f"for filter field '{filter_field}'"
                )
        elif all_sections_requested and filter_field and filter_field.strip():
            siemplify.LOGGER.info(
                f"All sections requested - no need to add specific section "
                f"for filter field '{filter_field}'"
            )

        # Convert sections list to comma-separated string for API
        sections_string = ",".join(sections_list) if sections_list else "GENERAL"

        siemplify.LOGGER.info(f"Final sections to request: {sections_string}")
        if filter_field and filter_field.strip():
            siemplify.LOGGER.info(
                f"Filter field '{filter_field}' requires section: "
                f"{get_section_for_filter_field(filter_field)}"
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

        # Get mobile device inventory
        siemplify.LOGGER.info("Retrieving mobile device inventory from Jamf Pro")
        mobile_devices = jamf_manager.get_mobile_device_inventory(
            page=page,
            page_size=page_size,
            sort=sort_string,
            filter_query=filter_string,
            section=sections_string,
        )

        if mobile_devices and mobile_devices.get("results"):
            device_count = len(mobile_devices["results"])
            total_count = mobile_devices.get("totalCount", device_count)

            siemplify.LOGGER.info(
                f"Successfully retrieved {device_count} mobile devices (Total: {total_count})"
            )

            json_result = {
                "page": page,
                "page_size": page_size,
                "sort_criteria": sort_string,
                "filter_criteria": filter_string,
                "sections_requested": sections_string,
                "inventory_data": mobile_devices,
            }

            siemplify.result.add_result_json(json_result)
            output_message = f"Successfully retrieved {device_count} mobile devices from Jamf Pro"
            result_value = True
        else:
            siemplify.LOGGER.info("No mobile devices found matching the criteria")
            output_message = "No mobile devices found matching the specified criteria"
            result_value = False

    except JamfError as e:
        siemplify.LOGGER.error(f"Jamf API error occurred: {e}")
        output_message = f"Failed to retrieve mobile device inventory: {e}"
        status = EXECUTION_STATE_FAILED
        result_value = False
    except Exception as e:
        siemplify.LOGGER.error(f"General error occurred: {e}")
        siemplify.LOGGER.exception(e)
        output_message = f"Failed to retrieve mobile device inventory: {e}"
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
