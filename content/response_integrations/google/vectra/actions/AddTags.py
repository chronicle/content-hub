# coding=utf-8
from __future__ import annotations
import copy
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.VectraManager import VectraManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, ADD_TAGS_SCRIPT_NAME
from ..core.VectraExceptions import (
    ItemNotFoundException,
    TagsUpdateFailException,
    UnknownTagsUpdateException,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_TAGS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration.
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Parameters
    item_type = extract_action_param(
        siemplify, param_name="Item Type", input_type=str, is_mandatory=True
    )
    item_id = extract_action_param(
        siemplify, param_name="Item ID", input_type=str, is_mandatory=True
    )
    tags = extract_action_param(
        siemplify, param_name="Tags", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "true"

    try:
        vectra_manager = VectraManager(
            api_root, api_token, verify_ssl=verify_ssl, siemplify=siemplify
        )
        received_item = vectra_manager.get_item_info(item_type, item_id)

        if not received_item:
            raise ItemNotFoundException(f"{item_type} with ID {item_id} was not found")

        existing_tags = copy.deepcopy(received_item.tags)
        new_tags = [t.strip() for t in tags.split(",") if t.strip()]
        existing_tags.extend(new_tags)
        vectra_manager.update_tags(item_type, item_id, existing_tags)
        output_message = (
            "Successfully added tags"
            f"{','.join(new_tags)} to {item_type} with ID {item_id}"
        )
        siemplify.LOGGER.info(output_message)

    except (
        ItemNotFoundException,
        TagsUpdateFailException,
        UnknownTagsUpdateException,
    ) as e:
        output_message = str(e)
        result_value = "false"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = f'Error executing action "Add Tags". Reason: {e}'
        result_value = "false"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
