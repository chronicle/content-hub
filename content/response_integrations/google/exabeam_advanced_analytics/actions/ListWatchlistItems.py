from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.ExabeamAdvancedAnalyticsManager import ExabeamAdvancedAnalyticsManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from ..core.consts import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_WATCHLIST_ITEMS_SCRIPT_NAME,
    DEFAULT_MAX_WATCHLIST_ITEMS_TO_RETURN,
    DEFAULT_WATCHLIST_ITEMS_MAX_DAYS_BACKWARDS,
    MIN_WATCHLIST_ITEMS_MAX_DAYS_BACKWARDS_TO_RETURN,
    MIN_WATCHLIST_ITEMS_TO_RETURN,
    WATCHLIST_USERS_CATEGORIES,
    WATCHLIST_USERS_TYPE,
    WATCHLIST_ASSETS_TYPE,
)
from ..core.utils import load_csv_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_WATCHLIST_ITEMS_SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    apit_token = extract_configuration_param(
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
    output_message = ""

    successful_watchlists = []
    failed_watchlists = []
    json_results = []

    try:
        # Action configuration
        watchlist_titles = extract_action_param(
            siemplify,
            param_name="Watchlist Titles",
            is_mandatory=True,
            print_value=True,
        )
        max_watchlist_items_to_return = extract_action_param(
            siemplify,
            param_name="Max Items To Return",
            default_value=DEFAULT_MAX_WATCHLIST_ITEMS_TO_RETURN,
            input_type=int,
            is_mandatory=False,
            print_value=True,
        )
        max_days_backwards = extract_action_param(
            siemplify,
            param_name="Max Days Backwards",
            default_value=DEFAULT_WATCHLIST_ITEMS_MAX_DAYS_BACKWARDS,
            input_type=int,
            is_mandatory=False,
            print_value=True,
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        if max_watchlist_items_to_return < MIN_WATCHLIST_ITEMS_TO_RETURN:
            siemplify.LOGGER.info(
                f'"Max Items To Return" must be non-negative. Using default of {DEFAULT_MAX_WATCHLIST_ITEMS_TO_RETURN}.'
            )
            max_watchlist_items_to_return = DEFAULT_MAX_WATCHLIST_ITEMS_TO_RETURN

        if max_days_backwards < MIN_WATCHLIST_ITEMS_MAX_DAYS_BACKWARDS_TO_RETURN:
            siemplify.LOGGER.info(
                f'"Max Days Backwards" parameter cannot be negative. Using default of {DEFAULT_WATCHLIST_ITEMS_MAX_DAYS_BACKWARDS} '
            )
            max_days_backwards = DEFAULT_WATCHLIST_ITEMS_MAX_DAYS_BACKWARDS

        manager = ExabeamAdvancedAnalyticsManager(
            api_root=api_root,
            api_token=apit_token,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )
        watchlist_titles = load_csv_to_list(
            csv=watchlist_titles, param_name="Watchlist Titles"
        )
        siemplify.LOGGER.info("Listing available watchlists")
        watchlists = manager.list_watchlists()
        siemplify.LOGGER.info(f"Successfully listed {len(watchlists)} watchlists")

        for watchlist in watchlists:
            if watchlist.title not in watchlist_titles:
                siemplify.LOGGER.info(f"Skipping watchlist {watchlist.title}...")
                continue

            try:
                siemplify.LOGGER.info(
                    f"Fetching items from watchlist {watchlist.title}"
                )

                detailed_watchlist = manager.get_watchlist(
                    watchlist_type=(
                        WATCHLIST_USERS_TYPE
                        if watchlist.category in WATCHLIST_USERS_CATEGORIES
                        else WATCHLIST_ASSETS_TYPE
                    ),
                    watchlist_id=watchlist.watchlist_id,
                    max_days_backwards=max_days_backwards,
                    items_limit=max_watchlist_items_to_return,
                )

                siemplify.LOGGER.info(
                    f"Successfully fetched {len(detailed_watchlist.items)} watchlist items."
                )

                json_results.append(detailed_watchlist.as_json())

                if detailed_watchlist.items:
                    siemplify.result.add_data_table(
                        title=f"Watchlist {watchlist.title} Items",
                        data_table=construct_csv(
                            [item.as_csv() for item in detailed_watchlist.items]
                        ),
                    )
                    successful_watchlists.append(watchlist.title)
                else:
                    failed_watchlists.append(watchlist.title)

            except Exception as error:
                failed_watchlists.append(watchlist.title)
                siemplify.LOGGER.error(
                    f"An error occurred on watchlist {watchlist.title}"
                )
                siemplify.LOGGER.exception(error)

        missing_watchlists = [
            watchlist_title
            for watchlist_title in watchlist_titles
            if watchlist_title not in successful_watchlists + failed_watchlists
        ]
        if missing_watchlists:
            siemplify.LOGGER.info(
                "The following watchlists were not found:\n {}".format(
                    "\n   ".join(missing_watchlists)
                )
            )
            failed_watchlists.extend(missing_watchlists)

        if successful_watchlists:
            output_message += "Successfully retrieve available items for the following watchlists in {}:\n   {}\n\n".format(
                INTEGRATION_DISPLAY_NAME, "\n   ".join(successful_watchlists)
            )
            siemplify.result.add_result_json(json_results)
            result_value = True
        else:
            output_message += f"No items were found for the provided watchlists in {INTEGRATION_DISPLAY_NAME}."

        if failed_watchlists and successful_watchlists:
            output_message += "Action was not able to retrieve available items for the following watchlists in {}:\n   {}\n\n".format(
                INTEGRATION_DISPLAY_NAME, "\n   ".join(failed_watchlists)
            )

    except Exception as error:
        output_message = f'Error executing action "{LIST_WATCHLIST_ITEMS_SCRIPT_NAME}". Reason: {error}'
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
