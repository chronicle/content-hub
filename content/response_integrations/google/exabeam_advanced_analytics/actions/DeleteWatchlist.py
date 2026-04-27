from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.ExabeamAdvancedAnalyticsManager import ExabeamAdvancedAnalyticsManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    DELETE_WATCHLIST_SCRIPT_NAME,
)
from ..core.exceptions import ExabeamAdvancedAnalyticsNotFoundError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {DELETE_WATCHLIST_SCRIPT_NAME}"
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

    # Action configuration
    watchlist_title = extract_action_param(
        siemplify, param_name="Watchlist Title", is_mandatory=True, print_value=True
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = ExabeamAdvancedAnalyticsManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )
        siemplify.LOGGER.info("Listing available watchlists")
        found_watchlist = next(
            iter(
                filter(
                    lambda watchlist: watchlist.title == watchlist_title,
                    manager.list_watchlists(),
                )
            ),
            None,
        )

        if not found_watchlist:
            raise ExabeamAdvancedAnalyticsNotFoundError(
                f'Watchlist "{watchlist_title}" was not found.'
            )

        manager.delete_watchlist(watchlist_id=found_watchlist.watchlist_id)

        output_message = f'Successfully deleted watchlist "{watchlist_title}" in {INTEGRATION_DISPLAY_NAME}'
        result_value = True

    except Exception as error:
        output_message = (
            f'Error executing action "{DELETE_WATCHLIST_SCRIPT_NAME}". Reason: {error}'
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
