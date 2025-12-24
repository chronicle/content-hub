from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param
from ..core.datamodels import IPLookup
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    COMMON_ACTION_ERROR_MESSAGE,
    IP_LOOKUP_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    DEFAULT_OFFSET,
    DEFAULT_LIMIT,
)
from ..core.utils import get_integration_params, validate_integer_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = IP_LOOKUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    ip_filter = extract_action_param(
        siemplify,
        param_name="IP Filter",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    address_state = extract_action_param(
        siemplify,
        param_name="Address State",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        default_value="Used",
    )
    scope = extract_action_param(
        siemplify,
        param_name="Scope",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    tag_filter = extract_action_param(
        siemplify,
        param_name="Tag Filter",
        input_type=str,
        is_mandatory=False,
        print_value=True,
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

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        offset = validate_integer_param(offset, "Offset", zero_allowed=True, allow_negative=False)
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)

        # --- Validations ---
        address_state = address_state.lower()
        # --- API Manager ---
        api_manager = APIManager(api_root, api_key, verify_ssl, siemplify)

        # --- API Call ---
        response = api_manager.ip_lookup(
            ip_filter=ip_filter,
            address_state=address_state,
            scope=scope,
            tag_filter=tag_filter,
            offset=offset,
            limit=limit,
            order_by=order_by,
        )
        results = response.get("results", [])
        table_results = []
        for item in results[:MAX_TABLE_RECORDS]:
            model = IPLookup(item)
            table_results.append(model.to_csv())

        output_message = (
            f"Successfully retrieved {len(results)} IP records. "
            f"Showing up to {MAX_TABLE_RECORDS} in table."
        )
        siemplify.result.add_result_json(json.dumps(response))
        if table_results:
            siemplify.result.add_data_table(
                title="IP Lookup Data", data_table=construct_csv(table_results)
            )
        else:
            output_message = "No IP data found."

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(IP_LOOKUP_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
