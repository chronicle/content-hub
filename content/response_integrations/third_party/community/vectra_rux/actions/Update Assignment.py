from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    INTEGRATION_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    UPDATE_ASSIGNMENT_SCRIPT_NAME,
)
from ..core.UtilsManager import validate_integer
from ..core.VectraRUXExceptions import (
    InvalidIntegerException,
    ItemNotFoundException,
    UserNotPermittedException,
    VectraRUXException,
)
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_ASSIGNMENT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
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
    user_id = extract_action_param(
        siemplify,
        param_name="User ID",
        input_type=str,
        is_mandatory=True,
    )
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
        entity_info = vectra_manager.get_specific_entity_info(entity_type, entity_id)

        # get assignment_id
        assignment_info = entity_info.get("assignment")
        if not assignment_info:
            raise ItemNotFoundException(
                f"Entity ID {entity_id} doesn't have assignment.",
            )
        assignment_id = assignment_info.get("id")

        # update assignment with given user_id
        response_data, assignments = vectra_manager.update_assignment(
            user_id,
            assignment_id,
        )
        output_message = (
            f"Successfully updated assignment-{assignment_id} to user ID-{user_id}"
        )
        siemplify.result.add_result_json(json.dumps(response_data, indent=4))

        # add response to csv
        siemplify.result.add_data_table(
            title="Updated Assignment",
            data_table=construct_csv([assignments.update_assignment_csv(entity_type)]),
        )

    except (
        UserNotPermittedException,
        InvalidIntegerException,
        ItemNotFoundException,
    ) as e:
        output_message = str(e)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraRUXException as e:
        output_message = f"Entity not found for the given ID: '{entity_id}'. Please verify the ID and try again."
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            UPDATE_ASSIGNMENT_SCRIPT_NAME,
            e,
        )
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
