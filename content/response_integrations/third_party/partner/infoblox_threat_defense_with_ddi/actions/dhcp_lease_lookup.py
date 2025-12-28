from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv

from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from TIPCommon import extract_action_param
from ..core.constants import (
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    COMMON_ACTION_ERROR_MESSAGE,
    DHCP_LEASE_LOOKUP_SCRIPT_NAME,
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    MAX_TABLE_RECORDS,
)
from ..core.datamodels import DHCPLease
from ..core.utils import get_integration_params, validate_integer_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DHCP_LEASE_LOOKUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    dhcp_lease_filter = extract_action_param(
        siemplify, param_name="DHCP Lease Filter", is_mandatory=False
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
        offset = validate_integer_param(offset, "Offset", zero_allowed=True, allow_negative=False)
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)

        infoblox_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = infoblox_manager.get_dhcp_lease_lookup(
            dhcp_lease_filter=dhcp_lease_filter, offset=offset, limit=limit, order_by=order_by
        )

        siemplify.result.add_result_json(response)
        results_data = response.get("results", [])
        if not results_data:
            output_message = "No DHCP lease records found."
        else:
            leases = [DHCPLease(lease).to_csv() for lease in results_data[:MAX_TABLE_RECORDS]]
            siemplify.result.add_data_table("DHCP Leases", construct_csv(leases))
            output_message = (
                f"Successfully retrieved {len(results_data)} DHCP lease record(s). "
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
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(DHCP_LEASE_LOOKUP_SCRIPT_NAME, e)
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
