from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    ASSIGN_ENTITY_SCRIPT_NAME,
    COMMON_ACTION_ERROR_MESSAGE,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import get_integration_params, validate_integer
from ..core.VectraRUXExceptions import InvalidIntegerException
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ASSIGN_ENTITY_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root, client_id, client_secret = get_integration_params(siemplify)

    user_id = siemplify.extract_action_param(
        param_name="User ID",
        input_type=str,
        is_mandatory=True,
    )

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

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        entity_id = validate_integer(entity_id, field_name="Entity ID")
        user_id = validate_integer(user_id, field_name="User ID")

        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )

        assignment = vectra_manager.assign_entity(entity_id, entity_type, user_id)
        output_message = (
            f"Assignment created successfully with ID: {assignment.assignment_id}"
        )

        siemplify.result.add_data_table(
            title="Assign Entity",
            data_table=assignment.create_assignment_csv(),
        )
        siemplify.result.add_result_json(json.dumps(assignment.raw_data, indent=4))

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"{e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"{e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
