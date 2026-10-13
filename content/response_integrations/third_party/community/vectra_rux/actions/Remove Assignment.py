from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    INTEGRATION_NAME,
    REMOVE_ASSIGNMENT_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import get_integration_params, validate_integer
from ..core.VectraRUXExceptions import InvalidIntegerException, VectraRUXException, ItemNotFoundException
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_ASSIGNMENT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration.
    api_root, client_id, client_secret = get_integration_params(siemplify)

    # Parameters
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

        # get entity info
        entity = vectra_manager.get_specific_entity_info(entity_type, entity_id)

        # get assignment_id
        if entity.get("assignment"):
            assignment_id = entity.get("assignment").get("id")

            # remove assignment
            result_value = vectra_manager.remove_assignment(assignment_id)
            
            if result_value:
                output_message = (
                    f"Successfully deleted assignment with entity ID {entity_id}"
                )
            else:
                result_value = RESULT_VALUE_FALSE
                status = EXECUTION_STATE_FAILED
                output_message = f"Failed to delete assignment with entity ID {entity_id}"
        else:
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED
            output_message = f"Entity ID {entity_id} doesn't have assignment."

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except ItemNotFoundException as e:
        output_message = f"Entity ID {entity_id} was not found. Please verify the Entity ID and Entity Type and try again."
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraRUXException as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(INTEGRATION_NAME, e)
        result_value = RESULT_VALUE_FALSE
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
