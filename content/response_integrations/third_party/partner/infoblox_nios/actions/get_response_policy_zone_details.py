from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_LIMIT,
    GET_RESPONSE_POLICY_ZONE_DETAILS_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import RPZone
from ..core.infoblox_exceptions import InfobloxException
from ..core.utils import get_integration_params, validate_integer_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RESPONSE_POLICY_ZONE_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, username, password, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    fqdn = extract_action_param(
        siemplify,
        param_name="FQDN",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    view = extract_action_param(
        siemplify,
        param_name="View",
        input_type=str,
        is_mandatory=False,
        default_value="default",
        print_value=True,
    )
    comment = extract_action_param(
        siemplify,
        param_name="Comment",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        # Parameter Validation
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        infoblox_manager = APIManager(
            api_root, username, password, verify_ssl=verify_ssl, siemplify=siemplify
        )
        rp_zones = infoblox_manager.get_rp_zone_details(
            fqdn=fqdn, view=view, comment=comment, limit=limit
        )
        siemplify.result.add_result_json(json.dumps(rp_zones, indent=4))

        if rp_zones:
            table_data = [RPZone(zone).to_csv() for zone in rp_zones[:MAX_TABLE_RECORDS]]
            siemplify.result.add_data_table("Response Policy Zones", construct_csv(table_data))
            output_message = f"Successfully retrieved {len(rp_zones)} RP zone(s). \
            Showing up to {MAX_TABLE_RECORDS} in table."
        else:
            output_message = "No RP zones found matching the criteria."

    except (InfobloxException, ValueError) as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_RESPONSE_POLICY_ZONE_DETAILS_SCRIPT_NAME, e
        )
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
