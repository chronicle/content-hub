from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    MANAGE_TAGS_IN_IOCS_SCRIPT_NAME,
    NO_ENTITIES_ERROR,
    NO_VALID_IOC_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE
)
from ..core.cyware_exceptions import CywareException
from ..core.utils import get_entities, get_integration_params, string_to_list


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = MANAGE_TAGS_IN_IOCS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    json_results: dict = {}

    try:
        base_url, access_id, secret_key, verify_ssl = get_integration_params(siemplify)
        tags_str = siemplify.extract_action_param("Tags", print_value=True, is_mandatory=True)
        operation_type = siemplify.extract_action_param(
            "Operation Type", print_value=True, is_mandatory=True
        )
        ioc_values = get_entities(siemplify)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        tag_names = string_to_list(tags_str, strip_quotes=True, param_name="Tags")

        if not ioc_values:
            output_message = NO_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        cyware_manager = APIManager(
            base_url.strip(), access_id, secret_key, verify_ssl=verify_ssl, siemplify=siemplify
        )

        # Fetch tag ids from names
        siemplify.LOGGER.info("Fetching tag ids from names")
        available_tags = cyware_manager.list_tags()
        tag_lookup = {
            (tag.get("name") or ""): tag.get("id")
            for tag in available_tags
            if tag.get("id") and tag.get("name")
        }

        tag_ids = [tag_lookup[tag] for tag in tag_names if tag in tag_lookup]
        invalid_tags = [tag for tag in tag_names if tag not in tag_lookup]

        if operation_type == "Add Tag":
            # Perform Add Operation
            siemplify.LOGGER.info("Fetching IOC ids from names")
            ioc_lookup = cyware_manager.lookup_iocs(ioc_values)
            invalid_iocs = [ioc for ioc in ioc_values if ioc not in ioc_lookup]
            object_ids = [ioc_lookup[ioc] for ioc in ioc_values if ioc in ioc_lookup]

            if not object_ids:
                output_message = NO_VALID_IOC_ERROR
                if invalid_iocs:
                    output_message += f" Invalid IOC(s): {', '.join(invalid_iocs)}."
                result_value = RESULT_VALUE_FALSE
                status = EXECUTION_STATE_COMPLETED
                return

            if invalid_tags:
                siemplify.LOGGER.info(
                    f"Creating the following missing tags in Cyware Intel Exchange: {invalid_tags}"
                )
                for tag in invalid_tags:
                    try:
                        created_tag = cyware_manager.create_tag(tag)
                        created_tag_id = created_tag.get("id")
                        if created_tag_id:
                            tag_lookup[tag] = created_tag_id
                            tag_ids.append(created_tag_id)
                            siemplify.LOGGER.info(
                                f"Successfully created tag '{tag}' with ID {created_tag_id}."
                            )
                        else:
                            siemplify.LOGGER.error(
                                f"Create tag response did not return an ID for tag '{tag}'."
                            )
                    except Exception as error:
                        siemplify.LOGGER.error(
                            f"Failed to create tag '{tag}' in Cyware Intel Exchange."
                        )
                        siemplify.LOGGER.exception(error)

            if not tag_ids:
                output_message = "No tags found to add to an IOC."
                result_value = RESULT_VALUE_FALSE
                status = EXECUTION_STATE_COMPLETED
                return

            response = cyware_manager.add_tags_to_ioc(object_ids=object_ids, tag_ids=tag_ids)

            if response:
                json_results = response
                output_message = (
                    f"Successfully added {len(tag_ids)} tag(s) to {len(object_ids)} IOC(s)."
                )
                notes = []
                if invalid_iocs:
                    notes.append(
                        f"Skipped invalid IOC(s) since they are not found on "
                        f"Cyware Intel Exchange: {', '.join(invalid_iocs)}."
                    )
                if notes:
                    output_message = f"{output_message} {' '.join(notes)}"
                result_value = RESULT_VALUE_TRUE
                siemplify.LOGGER.info(f"Add tags response: {json.dumps(response)}")
            else:
                output_message = "Failed to add tags to IOCs."
                result_value = RESULT_VALUE_FALSE
        else:
            # Perform Remove Operation
            if not tag_ids:
                output_message = "No valid tags found to remove. Please verify provided tag names."
                if invalid_tags:
                    output_message += f" Invalid tag(s): {', '.join(invalid_tags)}."
                result_value = RESULT_VALUE_FALSE
                status = EXECUTION_STATE_COMPLETED
                return

            siemplify.LOGGER.info("Resolving IOC values to object IDs")
            ioc_lookup = cyware_manager.lookup_iocs(ioc_values)
            invalid_iocs = [ioc for ioc in ioc_values if ioc not in ioc_lookup]
            object_ids = [ioc_lookup[ioc] for ioc in ioc_values if ioc in ioc_lookup]

            if not object_ids:
                output_message = NO_VALID_IOC_ERROR
                if invalid_iocs:
                    output_message += f" Invalid IOC(s): {', '.join(invalid_iocs)}."
                result_value = RESULT_VALUE_FALSE
                return

            response = cyware_manager.remove_tags_from_ioc(object_ids=object_ids, tag_ids=tag_ids)

            if response:
                json_results = response
                output_message = (
                    f"Successfully removed {len(tag_ids)} tag(s) from {len(object_ids)} IOC(s)."
                )
                notes = []
                if invalid_tags:
                    notes.append(f"Skipped invalid tag(s): {', '.join(invalid_tags)}.")
                if invalid_iocs:
                    notes.append(f"Skipped invalid IOC(s): {', '.join(invalid_iocs)}.")
                if notes:
                    output_message = f"{output_message} {' '.join(notes)}"
                result_value = RESULT_VALUE_TRUE
                siemplify.LOGGER.info(f"Remove tags response: {json.dumps(response)}")
            else:
                output_message = "Failed to remove tags from IOCs."
                result_value = RESULT_VALUE_FALSE

    except CywareException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(MANAGE_TAGS_IN_IOCS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.result.add_result_json(json_results)
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"result_value: {result_value}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
