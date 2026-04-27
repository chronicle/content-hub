from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_RECORDS_LIMIT,
    FILTER_KEY_MAPPING,
    FILTER_STRATEGY_MAPPING,
    INTEGRATION_NAME,
    LIST_PLAYBOOKS_ACTION,
    PRODUCT,
)
from ..core.CofenseTriageManager import CofenseTriageManager


TABLE_NAME = "Available Playbooks"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_PLAYBOOKS_ACTION
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", print_value=True
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        input_type=int,
        default_value=DEFAULT_RECORDS_LIMIT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = (
        f"Successfully found playbooks for the provided criteria in {PRODUCT}."
    )
    result_value = True

    try:
        if limit <= 0:
            raise Exception(
                f'Invalid value provided for "Max Records to Return": {limit}. '
                f"Positive number should be provided."
            )
        if limit > DEFAULT_PAGE_SIZE:
            siemplify.LOGGER.info(
                f'The maximum allowed value for "Max Records to Return" is '
                f'{DEFAULT_PAGE_SIZE}.'
                f"Using the default value: {DEFAULT_RECORDS_LIMIT}."
            )
            limit = DEFAULT_RECORDS_LIMIT

        if not FILTER_KEY_MAPPING.get(filter_key) and FILTER_STRATEGY_MAPPING.get(
            filter_logic
        ):
            raise Exception(
                'you need to select a field from the "Filter Key" parameter'
            )

        manager = CofenseTriageManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        playbooks = manager.get_playbooks(
            filter_key=FILTER_KEY_MAPPING.get(filter_key),
            filter_logic=FILTER_STRATEGY_MAPPING.get(filter_logic),
            filter_value=filter_value,
            limit=limit,
        )

        if playbooks:
            json_results = [playbook.to_json() for playbook in playbooks]
            csv_result = [playbook.to_csv() for playbook in playbooks]
            siemplify.result.add_data_table(
                title=TABLE_NAME, data_table=construct_csv(csv_result)
            )
            siemplify.result.add_result_json(json_results)

            if (
                FILTER_KEY_MAPPING.get(filter_key)
                and FILTER_STRATEGY_MAPPING.get(filter_logic)
                and filter_value is None
            ):
                output_message += ('\nThe filter was not applied, because'
                                   ' parameter "Filter Value" has an empty value.')

            if (
                FILTER_KEY_MAPPING.get(filter_key)
                and filter_value
                and not FILTER_STRATEGY_MAPPING.get(filter_logic)
            ):
                output_message += ('\nThe filter was not applied, because parameter '
                                   '"Filter Logic" is not specified.')
        else:
            result_value = False
            output_message = (
                f"No playbooks were found for the provided criteria in {PRODUCT}"
            )

    except Exception as e:
        output_message = (
            f'Error executing action "{LIST_PLAYBOOKS_ACTION}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
