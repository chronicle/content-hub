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
    DHCP_LEASE_LOOKUP_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import DHCPLeaseLookup
from ..core.infoblox_exceptions import InfobloxException
from ..core.utils import get_integration_params, validate_integer_param, validate_ip_address


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DHCP_LEASE_LOOKUP_SCRIPT_NAME
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
    hardware = extract_action_param(
        siemplify,
        param_name="Hardware",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    hostname = extract_action_param(
        siemplify,
        param_name="Hostname",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    ipv6_duid = extract_action_param(
        siemplify,
        param_name="IPv6 DUID",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    protocol = extract_action_param(
        siemplify,
        param_name="Protocol",
        input_type=str,
        is_mandatory=False,
        print_value=True,
        default_value="Both",
    ).upper()
    fingerprint = extract_action_param(
        siemplify,
        param_name="Fingerprint",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    user = extract_action_param(
        siemplify,
        param_name="Username",
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
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        validate_ip_address(ip_address)

        # --- API Manager ---
        api_manager = APIManager(
            api_root, username, password, verify_ssl=verify_ssl, siemplify=siemplify
        )

        # --- API Call ---
        results = api_manager.dhcp_lease_lookup(
            ip_address=ip_address,
            hardware=hardware,
            hostname=hostname,
            ipv6_duid=ipv6_duid,
            protocol=protocol,
            fingerprint=fingerprint,
            username=user,
            limit=limit,
        )
        table_results = []
        for item in results[:MAX_TABLE_RECORDS]:
            model = DHCPLeaseLookup(item)
            table_results.append(model.to_csv())

        output_message = (
            f"Successfully retrieved {len(results)} DHCP Lease records. "
            f"Showing up to {MAX_TABLE_RECORDS} in table."
        )
        siemplify.result.add_result_json(json.dumps(results))
        if table_results:
            siemplify.result.add_data_table(
                title="DHCP Lease Lookup Data", data_table=construct_csv(table_results)
            )
        else:
            output_message = "No DHCP Lease data found."

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(DHCP_LEASE_LOOKUP_SCRIPT_NAME, e)
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
