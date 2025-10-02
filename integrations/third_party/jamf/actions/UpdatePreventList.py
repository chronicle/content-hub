from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import (
    INTEGRATION_NAME,
    PROTECT_PREVENT_TYPE_MAP,
    UPDATE_PREVENT_LIST_SCRIPT_NAME,
)
from ..core.exceptions import JamfError
from ..core.JamfProtectManager import JamfProtectManager

if TYPE_CHECKING:
    from typing import NoReturn


@output_handler
def main() -> NoReturn:
    """
    Update prevent list in Jamf Protect.

    This action updates an existing prevent list in Jamf Protect.
    Supports multiple values as a comma-separated list.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_PREVENT_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = False

    try:
        # INIT INTEGRATION CONFIGURATION:
        jamf_protect_api_root = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Jamf Protect API Root",
            is_mandatory=True,
            print_value=True,
        )
        jamf_protect_client_api_id = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Jamf Protect Client API ID",
            is_mandatory=True,
            print_value=True,
        )
        jamf_protect_client_api_secret = extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Jamf Protect Client API Secret",
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
        prevent_list_name = extract_action_param(
            siemplify,
            param_name="Prevent List Name",
            is_mandatory=True,
            print_value=True,
        )
        prevent_list_description = extract_action_param(
            siemplify,
            param_name="Prevent List Description",
            is_mandatory=False,
            print_value=True,
        )
        prevent_type = extract_action_param(
            siemplify,
            param_name="Prevent Type",
            is_mandatory=True,
            print_value=True,
        )
        prevent_list_data = extract_action_param(
            siemplify,
            param_name="Prevent List Data",
            is_mandatory=True,
            print_value=False,
        )
        prevent_list_tags = extract_action_param(
            siemplify,
            param_name="Prevent List Tags",
            is_mandatory=False,
            print_value=True,
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        # Parse values from comma-separated string
        values_list = []
        if prevent_list_data and prevent_list_data.strip():
            values_list = [value.strip() for value in prevent_list_data.split(",") if value.strip()]
        siemplify.LOGGER.info(f"Parsed {len(values_list)} input values")

        # Parse tags from comma-separated string
        tags_list = []
        if prevent_list_tags and prevent_list_tags.strip():
            tags_list = [tag.strip() for tag in prevent_list_tags.split(",") if tag.strip()]
        siemplify.LOGGER.info(f"Parsed {len(tags_list)} input tags")

        # Create JamfManager instance
        jamf_protect_manager = JamfProtectManager(
            api_root=jamf_protect_api_root,
            client_api_id=jamf_protect_client_api_id,
            client_api_secret=jamf_protect_client_api_secret,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        prevent_lists = jamf_protect_manager.list_prevent_lists()
        if not prevent_lists:
            raise Exception("No prevent lists found")

        prevent_list_match = None
        for prevent_list in (
            prevent_lists.get("data", {}).get("listPreventLists", {}).get("items", [])
        ):
            if prevent_list.get("name") == prevent_list_name:
                prevent_list_match = prevent_list
                break

        if not prevent_list_match:
            raise Exception(f"Prevent list with name '{prevent_list_name}' does not exist")

        prevent_list_match_id = prevent_list_match.get("id")
        prevent_list_match_description = prevent_list_match.get("description")
        prevent_list_match_tags = prevent_list_match.get("tags")
        prevent_list_match_values = prevent_list_match.get("list")
        prevent_list_match_type = prevent_list_match.get("type")

        prevent_type_input = PROTECT_PREVENT_TYPE_MAP.get(prevent_type)

        if prevent_type_input != prevent_list_match_type:
            raise Exception("Prevent type cannot be changed")
        if not prevent_list_description:
            prevent_list_description = prevent_list_match_description

        # Validate values per prevent type
        validate_prevent_values(prevent_type_input, values_list)

        # Merge tags with existing (preserve order, dedupe)
        if tags_list:
            if prevent_list_match_tags:
                tags_list = list(dict.fromkeys((prevent_list_match_tags or []) + tags_list))
        else:
            if prevent_list_match_tags:
                tags_list = prevent_list_match_tags
            else:
                raise Exception("At least one tag must be provided")
        siemplify.LOGGER.info(f"Final tags count: {len(tags_list)}")

        if not values_list:
            raise Exception("At least one value must be provided")
        else:
            values_list = list(dict.fromkeys((prevent_list_match_values or []) + values_list))
        siemplify.LOGGER.info(f"Final values count: {len(values_list)}")

        result = jamf_protect_manager.update_prevent_list(
            name=prevent_list_name,
            description=prevent_list_description,
            prevent_type=prevent_type_input,
            values=values_list,
            tags=tags_list,
            id=prevent_list_match_id,
        )

        preview_values = ", ".join(map(str, values_list[:3]))
        if len(values_list) > 3:
            preview_values += f" (and {len(values_list) - 3} more)"
        preview_tags = ", ".join(map(str, tags_list[:3])) if tags_list else "None"

        output_message = (
            f"Successfully updated prevent list '{prevent_list_name}'.\n"
            f"Type: {prevent_list_match_type}.\n"
            f"Values set: {preview_values}.\n"
            f"Tags: {preview_tags}."
        )

        # Prepare comprehensive result
        json_result = {"status": "success", "prevent_list": result.get("data", {}).get("updatePreventList", {})}

        # Set JSON result
        siemplify.result.add_result_json(json_result)

        # Set execution state
        siemplify.LOGGER.info("Successfully completed Update Prevent List action")
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except JamfError as e:
        siemplify.LOGGER.error(f"Jamf API error while updating prevent list: {e}")
        siemplify.LOGGER.exception(e)
        output_message = f"Jamf API error: {str(e)}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        siemplify.LOGGER.error(f"Unexpected error while updating prevent list: {e}")
        siemplify.LOGGER.exception(e)
        output_message = f"Unexpected error: {str(e)}"
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output: {output_message}")

    siemplify.end(output_message, result_value, status)


# Local validation helpers for prevent list values
def _is_sha1(s: str) -> bool:
    return bool(re.fullmatch(r"^[A-Fa-f0-9]{40}$", str(s).strip()))


def _is_sha256(s: str) -> bool:
    return bool(re.fullmatch(r"^[A-Fa-f0-9]{64}$", str(s).strip()))


def _is_team_id(s: str) -> bool:
    # Apple Team ID is 10 uppercase alphanumeric characters
    return bool(re.fullmatch(r"^[A-Z0-9]{10}$", str(s).strip()))


def _is_signing_id(s: str) -> bool:
    # Bundle identifier style: segments of [A-Za-z0-9-]+ separated by dots,
    # must have at least one dot
    # Disallow leading/trailing dots and consecutive dots
    return bool(
        re.fullmatch(
            r"^[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)+$",
            str(s).strip(),
        )
    )


def validate_prevent_values(pt: str, values: list[str]) -> None:
    invalid: list[tuple[str, str]] = []
    for v in values or []:
        if pt == "FILEHASH":
            if not (_is_sha1(v) or _is_sha256(v)):
                invalid.append((v, "not SHA-1 or SHA-256 hash"))
        elif pt == "CDHASH":
            if not _is_sha1(v):
                invalid.append((v, "not SHA-1 hash"))
        elif pt == "TEAMID":
            if not _is_team_id(v):
                invalid.append((v, "invalid Apple Team ID (expected 10 uppercase alphanumerics)"))
        elif pt == "SIGNINGID":
            if not _is_signing_id(v):
                invalid.append((v, "invalid signing identifier"))

    if invalid:
        details = "; ".join([f"'{val}' ({reason})" for val, reason in invalid[:10]])
        more = f" and {len(invalid) - 10} more" if len(invalid) > 10 else ""
        raise Exception(f"Invalid values for Prevent Type '{pt}': {details}{more}")


if __name__ == "__main__":
    main()
