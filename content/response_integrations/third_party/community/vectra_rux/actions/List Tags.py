from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.transformation import flat_dict_to_csv

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    LIST_TAGS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import get_integration_params, validate_integer
from ..core.VectraRUXExceptions import VectraRUXException, ItemNotFoundException, InvalidIntegerException
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_TAGS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameter
    api_root, client_id, client_secret = get_integration_params(siemplify)

    # Action Parameters
    entity_id = siemplify.extract_action_param(
        param_name="Entity ID",
        input_type=str,
        is_mandatory=True,
    )
    entity_type = siemplify.extract_action_param(
        param_name="Entity Type",
        input_type=str,
        is_mandatory=True,
    ).lower()

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    try:
        entity_id = validate_integer(entity_id, field_name="Entity ID")

        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )

        entity_tags = vectra_manager.list_tags(entity_id, entity_type)
        tags = entity_tags.get("tags")

        if entity_tags.get("status") != "success":
            status = EXECUTION_STATE_FAILED
            result_value = RESULT_VALUE_FALSE
            output_message = "Failed to Fetch the Tags"
        else:
            output_message = f"Fetch List of Tags: {', '.join(tags)}"
            siemplify.result.add_data_table(
                title="List Entity Tags",
                data_table=(
                    flat_dict_to_csv(
                        {
                            "Entity ID": entity_id,
                            "Entity Type": entity_type,
                            "Tags": " | ".join(tags),
                            "Status": entity_tags.get("status")
                        }
                    )
                ),
            )

        siemplify.result.add_result_json(json.dumps(entity_tags))
    
    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.exception(e)
    except ItemNotFoundException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"Entity not found for the given ID: '{entity_id}'. Please verify the ID and try again."
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraRUXException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(LIST_TAGS_SCRIPT_NAME, e)
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
