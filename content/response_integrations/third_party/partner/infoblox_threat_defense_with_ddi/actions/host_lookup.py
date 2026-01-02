from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    COMMON_ACTION_ERROR_MESSAGE,
    HOST_LOOKUP_SCRIPT_NAME,
    DEFAULT_LIMIT,
    MAX_TABLE_RECORDS,
    DEFAULT_OFFSET,
)
from ..core.datamodels import Host
from ..core.utils import get_integration_params, validate_integer_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = HOST_LOOKUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    host_filter = extract_action_param(
        siemplify,
        param_name="Host Filter",
        is_mandatory=False,
        input_type=str,
    )
    tag_filter = extract_action_param(
        siemplify,
        param_name="Tag Filter",
        is_mandatory=False,
        input_type=str,
    )
    offset = extract_action_param(
        siemplify,
        param_name="Offset",
        input_type=str,
        default_value=DEFAULT_OFFSET,
        is_mandatory=False,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        default_value=DEFAULT_LIMIT,
        is_mandatory=False,
    )
    order_by = extract_action_param(
        siemplify,
        param_name="Order By",
        input_type=str,
        is_mandatory=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        # --- Validations ---
        offset = validate_integer_param(offset, "Offset", zero_allowed=True, allow_negative=False)
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)

        # --- API Manager ---
        infoblox_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = infoblox_manager.get_host_lookup(
            host_filter=host_filter,
            tag_filter=tag_filter,
            offset=offset,
            limit=limit,
            order_by=order_by,
        )

        siemplify.result.add_result_json(response)
        results_data = response.get("results", [])
        if not results_data:
            output_message = "No host asset records found."
        else:
            hosts = [Host(host).to_csv() for host in results_data[:MAX_TABLE_RECORDS]]
            siemplify.result.add_data_table("Hosts", construct_csv(hosts))
            output_message = (
                f"Successfully retrieved {len(results_data)} host asset record(s). "
                f"Showing up to {MAX_TABLE_RECORDS} in table."
            )

    except InfobloxException as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(HOST_LOOKUP_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
