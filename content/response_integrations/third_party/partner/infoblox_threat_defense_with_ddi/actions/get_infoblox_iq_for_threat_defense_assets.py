from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.APIManager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_LIMIT,
    GET_SOC_INSIGHTS_ASSETS_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    VERIFIED_MAPPING,
)
from ..core.datamodels import InfobloxIQForThreatDefenseAsset
from ..core.InfobloxExceptions import InfobloxException
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
    ip_address = extract_action_param(
        siemplify,
        param_name="IP Address",
        is_mandatory=False,
        input_type=str,
        default_value=None,
    )
    users = extract_action_param(siemplify, param_name="Users", is_mandatory=False, input_type=str, default_value=None)

    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        default_value=DEFAULT_LIMIT,
        is_mandatory=False,
    )
    is_verified = extract_action_param(
        siemplify, param_name="Is Verified", input_type=str, is_mandatory=False, default_value=None
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        validate_required_string(insight_id, "Insight ID")
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)

        infoblox_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = infoblox_manager.get_infoblox_iq_for_threat_defense_assets(
            insight_id=insight_id,
            ip_address=ip_address,
            users=users,
            limit=limit,
            is_verified=VERIFIED_MAPPING.get(is_verified, None),
        )

        siemplify.result.add_result_json(response)
        assets_data = response.get("assets", [])
        if not assets_data:
            output_message = f"No assets found for Insight ID: {insight_id}."
        else:
            assets = [InfobloxIQForThreatDefenseAsset(asset).to_csv() for asset in assets_data[:MAX_TABLE_RECORDS]]
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
