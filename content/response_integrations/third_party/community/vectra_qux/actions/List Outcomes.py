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
    LIST_OUTCOMES_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import validate_integer, validate_limit_param
from ..core.VectraQUXExceptions import InvalidIntegerException
from ..core.VectraQUXManager import VectraQUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_OUTCOMES_SCRIPT_NAME

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
    max_outcome_to_return = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = RESULT_VALUE_TRUE
    status = EXECUTION_STATE_COMPLETED

    try:
        max_outcome_to_return = validate_limit_param(max_outcome_to_return)
        max_outcome_to_return = validate_integer(
            max_outcome_to_return,
            zero_allowed=True,
            field_name="Limit",
        )
        vectra_manager = VectraQUXManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        outcomes_obj, outcomes = vectra_manager.get_outcome_list(max_outcome_to_return)

        if not outcomes:
            output_message = "No outcomes found"
        else:
            output_message = f"Successfully retrieved {len(outcomes)} Outcomes."
            siemplify.result.add_data_table(
                title="Outcome Details",
                data_table=construct_csv(
                    [outcome.list_outcome_csv() for outcome in outcomes_obj],
                ),
            )

        siemplify.result.add_result_json(json.dumps(outcomes, indent=4))

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        output_message = f"{e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            LIST_OUTCOMES_SCRIPT_NAME,
            e,
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
