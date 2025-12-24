from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    INTEGRATION_NAME,
    REMOVE_ASSIGNMENT_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import validate_integer
from ..core.VectraQUXExceptions import InvalidIntegerException, VectraQUXException
from ..core.VectraQUXManager import VectraQUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_ASSIGNMENT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
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

    # Action Parameters
    entity_id = extract_action_param(
        siemplify,
        param_name="Entity ID",
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

    try:
        entity_id = validate_integer(entity_id, field_name="Entity ID")
        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        # get entity info
        received_info = vectra_manager.describe_entity(entity_id, entity_type)
        entity = received_info.raw_data

        # get assignment_id
        if entity.get("assignment"):
            assignment_id = entity.get("assignment").get("id")

            # remove assignment
            result_value = vectra_manager.remove_assignment(assignment_id)
            output_message = f"Successfully deleted assignment of entity ID {entity_id}"
        else:
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED
            output_message = f"Entity ID {entity_id} doesn't have assignment."

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"{e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraQUXException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"Entity not found for the given ID: '{entity_id}'. Please verify the ID and try again."
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
