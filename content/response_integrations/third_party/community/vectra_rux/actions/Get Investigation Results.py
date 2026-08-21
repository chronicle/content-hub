from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GET_INVESTIGATION_RESULTS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import get_integration_params, validate_limit_param, validate_integer
from ..core.VectraRUXExceptions import InvalidIntegerException, ItemNotFoundException, VectraRUXException
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_INVESTIGATION_RESULTS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, client_id, client_secret = get_integration_params(siemplify)

    # Action Parameters
    request_id = siemplify.extract_action_param(
        param_name="Request ID",
        input_type=str,
        is_mandatory=True,
    ).strip()

    limit = siemplify.extract_action_param(
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        limit = validate_integer(
            validate_limit_param(limit),
            zero_allowed=True,
            field_name="Limit",
        )

        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )

        investigation_results = vectra_manager.get_investigation_results(
            request_id,
            limit,
        )

        if not investigation_results:
            output_message = (
                f"No investigation results were found for request ID {request_id}."
            )
            siemplify.result.add_result_json(json.dumps([], indent=4))
        else:
            output_message = f"Retrieved {len(investigation_results)} investigation results for {request_id}."

            siemplify.result.add_data_table(
                title="Get Investigation Results",
                data_table=construct_csv(
                    [result.to_csv() for result in investigation_results],
                ),
            )
            siemplify.result.add_result_json(
                json.dumps(
                    [result.raw_data for result in investigation_results],
                    indent=4,
                ),
            )

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except ItemNotFoundException as e:
        status = EXECUTION_STATE_FAILED
        output_message = "Failed to get investigation result for given request id. Please provide valid request id."
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraRUXException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"{e}, while performing action {GET_INVESTIGATION_RESULTS_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_INVESTIGATION_RESULTS_SCRIPT_NAME,
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
