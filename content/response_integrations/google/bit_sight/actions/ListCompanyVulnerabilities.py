from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from bit_sight.core.BitSightManager import BitSightManager
from bit_sight.core.utils import validate_positive_integer
from bit_sight.core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_COMPANY_VULNERABILITIES_SCRIPT_NAME,
    DEFAULT_VULNERABILITIES_LIMIT,
)

TABLE_NAME = 'Company "{}" Vulnerabilities'


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_COMPANY_VULNERABILITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    company_name = extract_action_param(
        siemplify, param_name="Company Name", is_mandatory=True, print_value=True
    )
    only_high_confidence = extract_action_param(
        siemplify, param_name="Only High Confidence", input_type=bool, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Vulnerabilities To Return",
        input_type=int,
        default_value=DEFAULT_VULNERABILITIES_LIMIT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = f'No vulnerabilities were found for the "{company_name}" company in {INTEGRATION_DISPLAY_NAME}.'

    try:
        validate_positive_integer(
            number=limit,
            err_msg="Max Vulnerabilities To Return should be greater than zero.",
        )

        manager = BitSightManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        company = next(
            (item for item in manager.get_companies() if item.name == company_name),
            None,
        )

        if not company:
            raise Exception(
                f'company "{company_name}" wasn\'t found in {INTEGRATION_DISPLAY_NAME}. '
                f"Please check the spelling."
            )

        statistics = manager.get_company_vulnerabilities(
            company_id=company.guid, high_confidence=only_high_confidence
        )
        stats_list = []

        if statistics:
            vulnerabilities = statistics[0].vulnerabilities[:limit]

            if vulnerabilities:
                stats_list.extend(
                    [vulnerability.to_json() for vulnerability in vulnerabilities]
                )
                siemplify.result.add_data_table(
                    TABLE_NAME.format(company_name),
                    construct_csv(
                        [vulnerability.to_csv() for vulnerability in vulnerabilities]
                    ),
                )

                output_message = (
                    f'Successfully returned information about the "{company_name}" company '
                    f"vulnerabilities in {INTEGRATION_DISPLAY_NAME}."
                )

        siemplify.result.add_result_json({"stats": stats_list})

    except Exception as e:
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"General error performing action {LIST_COMPANY_VULNERABILITIES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        output_message = f'Error executing action "{LIST_COMPANY_VULNERABILITIES_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
