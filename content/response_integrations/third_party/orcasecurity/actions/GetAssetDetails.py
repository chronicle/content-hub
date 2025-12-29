from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from urllib.parse import urljoin
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.OrcaSecurityManager import OrcaSecurityManager
from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType
from ..core.constants import (
    INTEGRATION_NAME,
    GET_ASSET_DETAILS_SCRIPT_NAME,
    ASSETS_TABLE_NAME,
    DEFAULT_MAX_LIMIT,
)
from ..core.UtilsManager import string_to_multi_value, validate_positive_integer


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ASSET_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    ui_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="UI Root",
        is_mandatory=True,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=False,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    asset_ids = string_to_multi_value(
        extract_action_param(siemplify, param_name="Asset IDs", is_mandatory=True, print_value=True)
    )
    return_vulnerabilities = extract_action_param(
        siemplify,
        param_name="Return Vulnerabilities Information",
        print_value=True,
        input_type=bool,
    )
    lowest_severity = extract_action_param(
        siemplify,
        param_name="Lowest Severity For Vulnerabilities",
        print_value=True,
        default_value="Hazardous",
    )
    max_vulnerabilities_to_return = extract_action_param(
        siemplify,
        param_name="Max Vulnerabilities To Fetch",
        print_value=True,
        default_value=50,
        input_type=int,
    )
    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", print_value=True, input_type=bool
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_result, csv_result = [], []
    successful_assets, failed_assets = [], []

    try:
        validate_positive_integer(
            number=max_vulnerabilities_to_return,
            err_msg="Max Vulnerabilities To Fetch should be positive",
        )

        if max_vulnerabilities_to_return > DEFAULT_MAX_LIMIT:
            raise Exception(
                f"Max Vulnerabilities To Fetch parameter should be less than maximum limit "
                f"parameter: {DEFAULT_MAX_LIMIT}"
            )

        manager = OrcaSecurityManager(
            api_root=api_root,
            api_key=api_key,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        for asset_id in asset_ids:
            try:
                asset_data = manager.get_asset_details(asset_id=asset_id)
                asset_json = asset_data.to_json()

                if return_vulnerabilities:
                    vulnerabilities = manager.get_vulnerability_details(
                        asset_id=asset_id,
                        severity=lowest_severity,
                        limit=max_vulnerabilities_to_return,
                    )

                    asset_json.update({
                        "vulnerabilities": [
                            vulnerability.to_json() for vulnerability in vulnerabilities
                        ]
                    })

                json_result.append(asset_json)
                csv_result.append(asset_data.to_csv())
                successful_assets.append(asset_id)

                if create_insight:
                    siemplify.create_case_insight(
                        triggered_by=INTEGRATION_NAME,
                        title=f"{asset_id}",
                        content=asset_data.to_insight(
                            asset_link=urljoin(ui_root, f"inventory/{asset_id}")
                        ),
                        entity_identifier="",
                        severity=InsightSeverity.INFO,
                        insight_type=InsightType.General,
                    )

            except Exception as e:
                failed_assets.append(asset_id)
                siemplify.LOGGER.error(f"An error occurred on asset with id: {asset_id}. {e}.")
                siemplify.LOGGER.exception(e)

        if successful_assets:
            siemplify.result.add_result_json(json_result)
            siemplify.result.add_data_table(ASSETS_TABLE_NAME, construct_csv(csv_result))

            output_message += (
                f"Successfully enriched the following assets using information from {INTEGRATION_NAME}:"
                f" {', '.join(successful_assets)}\n"
            )

            if failed_assets:
                output_message += (
                    f"Action wasn't able to enrich the following assets using information from "
                    f"{INTEGRATION_NAME}: {', '.join(failed_assets)}\n"
                )

        else:
            output_message = "None of the provided assets were enriched."
            result_value = False

    except Exception as e:
        output_message = f"Error executing action {GET_ASSET_DETAILS_SCRIPT_NAME}. Reason: {e}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
