from __future__ import annotations

import copy
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    ENTITY_ID,
    INTEGRATION_NAME,
    REMOVE_TAGS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import validate_integer
from ..core.VectraRUXExceptions import (
    ItemNotFoundException,
    TagsUpdateFailException,
    VectraRUXException,
)
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_TAGS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameter
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        print_value=False,
        is_mandatory=True,
    )

    # Action Parameters
    tags = extract_action_param(
        siemplify,
        param_name="Tags",
        input_type=str,
        is_mandatory=True,
    )
    entity_id = extract_action_param(
        siemplify,
        param_name=ENTITY_ID,
        input_type=str,
        is_mandatory=True,
    )
    entity_type = extract_action_param(
        siemplify,
        param_name="Entity Type",
        input_type=str,
        is_mandatory=True,
    ).lower()

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    # Creating list of tags and remove duplicate tags
    new_tags = list({t.strip() for t in tags.split(",") if t.strip()})

    try:
        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )

        result_table = []  # Store the json response for each entity
        successfully_removed_tags = []  # Store the tags which is removed Successfully
        failed_remove_tags = []  # Store the tags which is failed to remove

        # Validating Entity ID
        entity_id = validate_integer(entity_id, field_name=ENTITY_ID)

        # Fetching Existing Tags for the Entity
        entity_tags = vectra_manager.get_entity_tags(
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if entity_tags is None:
            raise ItemNotFoundException(
                f"{entity_type} with ID {entity_id} was not found",
            )

        # Removing given tags from the list
        existing_tags = copy.deepcopy(entity_tags)
        for tag in new_tags:
            if tag in existing_tags:
                entity_tags.remove(tag)
                successfully_removed_tags.append(tag)
                siemplify.LOGGER.error(
                    f'Removed "{tag}" from {entity_type} with "{entity_id}"',
                )
            else:
                failed_remove_tags.append(tag)
                siemplify.LOGGER.error(
                    f'Tag "{tag}" not exist {entity_type} with "{entity_id}"',
                )

        # Raising Exception if tags was not removed
        if not successfully_removed_tags:
            raise TagsUpdateFailException(
                f"Tags {new_tags} don't exist in {entity_type} with ID {entity_id}",
            )
        # Updating the tags
        response = vectra_manager.update_tags(entity_type, entity_id, entity_tags)
        result_table.append(
            {
                ENTITY_ID: entity_id,
                "Entity Type": entity_type,
                "Status": response.get("status"),
                "Tags": response.get("tags"),
            },
        )

        if successfully_removed_tags and failed_remove_tags:
            output_message = f'Successfully removed tag(s):"{", ".join(successfully_removed_tags)}".Unable to remove tag(s):"{", ".join(failed_remove_tags)}" from {entity_type}: "{entity_id}". Check logs for details.'
        elif not successfully_removed_tags and failed_remove_tags:
            output_message = f'Failed to remove tag(s):"{", ".join(failed_remove_tags)}" from {entity_type}: "{entity_id}"'
        else:
            output_message = f'Successfully removed tag(s): "{", ".join(successfully_removed_tags)}" from {entity_type}: "{entity_id}"'

        # Logging
        siemplify.LOGGER.info(output_message)
        siemplify.result.add_result_json(json.dumps(result_table))
        siemplify.result.add_data_table(
            title="Tag Updated Status",
            data_table=construct_csv(result_table),
        )

    except VectraRUXException as e:
        output_message = f"{e}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(REMOVE_TAGS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
