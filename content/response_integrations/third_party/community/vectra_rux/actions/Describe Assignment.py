from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.transformation import flat_dict_to_csv

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DESCRIBE_ASSIGNMENT_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import get_integration_params, validate_integer
from ..core.VectraRUXExceptions import InvalidIntegerException, ItemNotFoundException
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DESCRIBE_ASSIGNMENT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, client_id, client_secret = get_integration_params(siemplify)

    # Action Parameters
    assignment_id = siemplify.extract_action_param(
        param_name="Assignment ID",
        input_type=str,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = RESULT_VALUE_TRUE
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        assignment_id = validate_integer(assignment_id, field_name="Assignment ID")
        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )

        response, assignment_info = vectra_manager.describe_assignment(assignment_id)

        output_message = (
            f"Successfully retrieved information for assignment ID {assignment_id}."
        )

        siemplify.result.add_result_json(json.dumps(response, indent=4))
        siemplify.result.add_data_table(
            title="Describe Assignment",
            data_table=flat_dict_to_csv(assignment_info.list_assignment_csv()),
        )
    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"{e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except ItemNotFoundException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"Assignment not found for the given ID: '{assignment_id}'. Please verify the ID and try again."
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            DESCRIBE_ASSIGNMENT_SCRIPT_NAME,
            e,
        )
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
