from __future__ import annotations

import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    INTEGRATION_NAME,
    LIST_ENTITY_DETECTIONS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import validate_integer, validate_limit_param
from ..core.VectraQUXExceptions import InvalidIntegerException
from ..core.VectraQUXManager import VectraQUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ENTITY_DETECTIONS_SCRIPT_NAME

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
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
    )
    state = extract_action_param(
        siemplify,
        param_name="State",
        input_type=str,
        is_mandatory=False,
    ).lower()

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        entity_id = validate_integer(entity_id, field_name="Entity ID")
        limit = validate_limit_param(limit)
        limit = validate_integer(limit, zero_allowed=True, field_name="Limit")

        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        detections = vectra_manager.list_entity_detections(
            entity_id,
            entity_type,
            limit,
            state,
        )

        if not len(detections):
            output_message = f"No detections found for entity ID {entity_id}"
            siemplify.result.add_result_json(json.dumps(detections, indent=4))
        else:
            output_message = f"Successfully retrieved {len(detections)} detections for entity ID {entity_id}."
            detections_json = [detection.to_json() for detection in detections]
            siemplify.result.add_result_json(json.dumps(detections_json, indent=4))
            siemplify.result.add_data_table(
                title="List Entity Detections",
                data_table=construct_csv(
                    [detection.get_subset() for detection in detections],
                ),
            )

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"{e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            LIST_ENTITY_DETECTIONS_SCRIPT_NAME,
            e,
        )
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
