from __future__ import annotations

import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_LIMIT,
    IP_LOOKUP_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import IPLookup
from ..core.infoblox_exceptions import InfobloxException
from ..core.utils import (
    get_integration_params,
    validate_integer_param,
    validate_ip_address,
    validate_network_address,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = IP_LOOKUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, username, password, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    ip_address = extract_action_param(
        siemplify,
        param_name="IP Address",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    network = extract_action_param(
        siemplify,
        param_name="Network",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    from_ip = extract_action_param(
        siemplify,
        param_name="From IP",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    to_ip = extract_action_param(
        siemplify,
        param_name="To IP",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    ip_status = extract_action_param(
        siemplify,
        param_name="Status",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        default_value="All",
    ).upper()
    extended_attributes = extract_action_param(
        siemplify,
        param_name="Extended Attributes",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        default_value=DEFAULT_LIMIT,
        is_mandatory=False,
    )
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        # Validation
        if not ip_address and not network and not (from_ip or to_ip):
            raise ValueError(
                "At least one of the following parameters must be provided: "
                "IP Address, Network, or From IP/To IP."
            )
        if sum(bool(arg) for arg in [ip_address, network, from_ip or to_ip]) > 1:
            raise ValueError(
                "Please specify only one of the `IP Address`, `Network` or (`From IP`/`To IP`)"
                + " Parameters"
            )
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        validate_ip_address(ip_address)
        validate_network_address(network)
        validate_ip_address(from_ip, "From IP")
        validate_ip_address(to_ip, "To IP")
        # --- API Manager ---
        api_manager = APIManager(api_root, username, password, verify_ssl, siemplify)
        # --- API Call ---
        response = api_manager.ip_lookup(
            ip_address=ip_address,
            network=network,
            from_ip=from_ip,
            to_ip=to_ip,
            ip_status=ip_status,
            extended_attributes=extended_attributes,
            limit=limit,
        )
        table_results = []
        for item in response[:MAX_TABLE_RECORDS]:
            model = IPLookup(item)
            table_results.append(model.to_csv())

        output_message = (
            f"Successfully retrieved {len(response)} IP records. "
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
