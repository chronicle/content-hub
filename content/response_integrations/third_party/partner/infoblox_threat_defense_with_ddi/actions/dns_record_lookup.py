from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param
from ..core.datamodels import DNSRecord
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    DNS_RECORD_LOOKUP_SCRIPT_NAME,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_OFFSET,
    DEFAULT_LIMIT,
    MAX_TABLE_RECORDS,
)
from ..core.utils import validate_integer_param, get_integration_params


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DNS_RECORD_LOOKUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    dns_record_filter = extract_action_param(
        siemplify,
        param_name="DNS Record Filter",
        input_type=str,
        is_mandatory=False,
    )
    tag_filter = extract_action_param(
        siemplify,
        param_name="Tag Filter",
        input_type=str,
        is_mandatory=False,
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
    try:
        offset = validate_integer_param(offset, "Offset", zero_allowed=True, allow_negative=False)
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        response = api_manager.dns_record_lookup(
            dns_record_filter=dns_record_filter,
            tag_filter=tag_filter,
            offset=offset,
            limit=limit,
            order_by=order_by,
        )
        results = response.get("results", response)

        table_results = []
        for item in results[:MAX_TABLE_RECORDS]:
            model = DNSRecord(item)
            table_results.append(model.to_csv())

        output_message = (
            f"Successfully retrieved {len(results)} DNS record(s). "
            f"Showing up to {MAX_TABLE_RECORDS} in table."
        )
        siemplify.result.add_result_json(json.dumps(response, indent=4))
        # Table view (using datamodel)
        if table_results:
            siemplify.result.add_data_table("DNS Records", construct_csv(table_results))
        else:
            output_message = "No DNS records found."

    except InfobloxException as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(DNS_RECORD_LOOKUP_SCRIPT_NAME, e)
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
