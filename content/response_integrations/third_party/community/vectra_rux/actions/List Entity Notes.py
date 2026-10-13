from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    LIST_ENTITY_NOTES_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import get_integration_params, validate_integer
from ..core.VectraRUXExceptions import InvalidIntegerException, ItemNotFoundException, VectraRUXException
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ENTITY_NOTES_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
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

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        entity_id = validate_integer(entity_id, field_name="Entity ID")

        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )

        notes = vectra_manager.list_entity_notes(entity_type, entity_id)

        if not notes:
            output_message = f"No notes were found for entity ID {entity_id}"
            siemplify.result.add_result_json(json.dumps([], indent=4))
        else:
            output_message = f"Successfully retrieved {len(notes)} entity notes"

            siemplify.result.add_data_table(
                title="List Entity Notes",
                data_table=construct_csv(
                    [note.list_entity_notes_csv() for note in notes],
                ),
            )
            siemplify.result.add_result_json(
                json.dumps([note.raw_data for note in notes], indent=4),
            )

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
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
        siemplify.LOGGER.error(
            f"{e}, while performing action {LIST_ENTITY_NOTES_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            LIST_ENTITY_NOTES_SCRIPT_NAME,
            e,
        )
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
