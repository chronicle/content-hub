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
    GET_SOC_INSIGHTS_ASSETS_SCRIPT_NAME,
    DEFAULT_LIMIT,
    MAX_TABLE_RECORDS,
)
from ..core.datamodels import SOCInsightAsset
from ..core.utils import get_integration_params, validate_integer_param, validate_required_string


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SOC_INSIGHTS_ASSETS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    insight_id = extract_action_param(
        siemplify,
        param_name="Insight ID",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    asset_ip = extract_action_param(
        siemplify,
        param_name="Asset IP",
        is_mandatory=False,
        input_type=str,
    )
    mac_address = extract_action_param(
        siemplify,
        param_name="MAC Address",
        is_mandatory=False,
        input_type=str,
    )
    os_version = extract_action_param(
        siemplify,
        param_name="OS Version",
        is_mandatory=False,
        input_type=str,
    )
    user = extract_action_param(siemplify, param_name="User", is_mandatory=False, input_type=str)

    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        default_value=DEFAULT_LIMIT,
        is_mandatory=False,
    )
    from_time = extract_action_param(siemplify, param_name="From", is_mandatory=False)
    to_time = extract_action_param(siemplify, param_name="To", is_mandatory=False)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        validate_required_string(insight_id, "Insight ID")
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)

        infoblox_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = infoblox_manager.get_soc_insights_assets(
            insight_id=insight_id,
            asset_ip=asset_ip,
            mac_address=mac_address,
            os_version=os_version,
            user=user,
            limit=limit,
            from_time=from_time,
            to_time=to_time,
        )

        siemplify.result.add_result_json(response)
        assets_data = response.get("assets", [])
        if not assets_data:
            output_message = f"No assets found for Insight ID: {insight_id}."
        else:
            assets = [SOCInsightAsset(asset).to_csv() for asset in assets_data[:MAX_TABLE_RECORDS]]
            siemplify.result.add_data_table("Assets", construct_csv(assets))
            output_message = (
                f"Successfully retrieved {len(assets_data)} asset(s) for Insight ID: {insight_id}. "
                f"Showing up to {MAX_TABLE_RECORDS} in table."
            )

    except (InfobloxException, ValueError) as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_SOC_INSIGHTS_ASSETS_SCRIPT_NAME, e)
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
