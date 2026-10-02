from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    CLOSE_ENTITY_DETECTIONS_SCRIPT_NAME,
    COMMON_ACTION_ERROR_MESSAGE,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import get_integration_params, validate_integer
from ..core.VectraRUXExceptions import (
    InvalidIntegerException,
    ItemNotFoundException,
    VectraRUXException,
)
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CLOSE_ENTITY_DETECTIONS_SCRIPT_NAME
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
    reason = siemplify.extract_action_param(
        param_name="Reason",
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

        # Fetching the entity to get the list of associated detection IDs
        entity = vectra_manager.describe_entity(entity_id, entity_type)
        close_detections = {}

        if not entity.detection_ids:
            output_message = f"No detections found for entity ID {entity_id}"
        else:
            # Closing all the detections associated with the entity
            close_detections = vectra_manager.close_detections(entity.detection_ids, reason)
            output_message = (
                f"The detections of the provided entity ID have been "
                f"successfully closed as {reason}"
            )
           
        siemplify.result.add_result_json(json.dumps(close_detections, indent=4))

    except InvalidIntegerException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except ItemNotFoundException as e:
        output_message = f"Entity not found for the given ID: '{entity_id}'. Please verify the ID and try again."
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraRUXException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            CLOSE_ENTITY_DETECTIONS_SCRIPT_NAME,
            e,
        )
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
