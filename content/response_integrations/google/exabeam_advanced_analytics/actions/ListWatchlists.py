from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.ExabeamAdvancedAnalyticsManager import ExabeamAdvancedAnalyticsManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from ..core.consts import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_WATCHLISTS_SCRIPT_NAME,
    DEFAULT_MAX_WATCHLISTS_TO_RETURN,
    MIN_WATCHLISTS_TO_RETURN,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_WATCHLISTS_SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        # Action configuration
        max_watchlists_to_return = extract_action_param(
            siemplify,
            param_name="Max Watchlists To Return",
            default_value=DEFAULT_MAX_WATCHLISTS_TO_RETURN,
            input_type=int,
            is_mandatory=False,
            print_value=True,
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        if max_watchlists_to_return < MIN_WATCHLISTS_TO_RETURN:
            siemplify.LOGGER.info(
                f'"Max Watchlist To Return" must be non-negative. Using default of {DEFAULT_MAX_WATCHLISTS_TO_RETURN}.'
            )
            max_watchlists_to_return = DEFAULT_MAX_WATCHLISTS_TO_RETURN

        manager = ExabeamAdvancedAnalyticsManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info("Listing available watchlists")
        watchlists = manager.list_watchlists(max_results=max_watchlists_to_return)

        if watchlists:
            output_message = f"Successfully retrieved available watchlists from {INTEGRATION_DISPLAY_NAME}"
            siemplify.result.add_result_json(
                [watchlist.as_json() for watchlist in watchlists]
            )
            siemplify.result.add_data_table(
                title="Available Watchlists",
                data_table=construct_csv(
                    [watchlist.as_csv() for watchlist in watchlists]
                ),
            )
            result_value = True
        else:
            output_message = f"No watchlists were found in {INTEGRATION_DISPLAY_NAME}"

    except Exception as error:
        output_message = (
            f'Error executing action "{LIST_WATCHLISTS_SCRIPT_NAME}". Reason: {error}'
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
