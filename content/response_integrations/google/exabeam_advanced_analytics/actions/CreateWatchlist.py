from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.ExabeamAdvancedAnalyticsManager import ExabeamAdvancedAnalyticsManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    CREATE_WATCHLIST_SCRIPT_NAME,
    DEFAULT_WATCHLIST_CATEGORY,
    DEFAULT_WATCHLIST_ACCESS_CONTROL,
    WATCHLIST_ACCESS_CONTROL_MAPPINGS,
    WATCHLIST_CATEGORY_MAPPINGS,
)
from ..core.exceptions import ExabeamAdvancedAnalyticsUnsuccessfulOperationError

SUPPORTED_ENTITIES = [EntityTypes.USER, EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {CREATE_WATCHLIST_SCRIPT_NAME}"
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
        siemplify, param_name="Title", is_mandatory=True, print_value=True
    )
    watchlist_category = extract_action_param(
        siemplify,
        param_name="Category",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_WATCHLIST_CATEGORY,
    )
    watchlist_access_control = extract_action_param(
        siemplify,
        param_name="Access Control",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_WATCHLIST_ACCESS_CONTROL,
    )
    watchlist_description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, print_value=True
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

        watchlist_access_control = WATCHLIST_ACCESS_CONTROL_MAPPINGS.get(
            watchlist_access_control
        )
        watchlist_category = WATCHLIST_CATEGORY_MAPPINGS.get(watchlist_category)

        created_watchlist = manager.create_watchlist(
            watchlist_title=watchlist_title,
            watchlist_category=watchlist_category,
            watchlist_access_control=watchlist_access_control,
            watchlist_description=watchlist_description,
        )

        output_message = f'Successfully created watchlist "{watchlist_title}" in {INTEGRATION_DISPLAY_NAME}'
        siemplify.result.add_result_json(created_watchlist.as_json())
        result_value = True

    except ExabeamAdvancedAnalyticsUnsuccessfulOperationError as error:
        output_message = f"Action wasn't able to create watchlist in {INTEGRATION_DISPLAY_NAME}. Reason: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f'Error executing action "{CREATE_WATCHLIST_SCRIPT_NAME}". Reason: {error}'
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
