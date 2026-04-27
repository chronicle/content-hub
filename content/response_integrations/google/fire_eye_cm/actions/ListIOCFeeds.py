from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.FireEyeCMConstants import (
    PROVIDER_NAME,
    DEFAULT_MAX_IOC_FEEDS_TO_RETURN,
    LIST_IOC_FEEDS_SCRIPT_NAME,
    MIN_IOC_FEEDS_TO_RETURN,
)
from ..core.FireEyeCMManager import FireEyeCMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_IOC_FEEDS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Init Integration Configurations
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=False,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    manager = None
    output_message = ""

    try:
        # Init Action Parameters
        max_ioc_feeds_to_return = extract_action_param(
            siemplify,
            param_name="Max IOC Feeds To Return",
            is_mandatory=False,
            input_type=int,
            default_value=DEFAULT_MAX_IOC_FEEDS_TO_RETURN,
            print_value=True,
        )

        if max_ioc_feeds_to_return < MIN_IOC_FEEDS_TO_RETURN:
            siemplify.LOGGER.info(
                f'"Max IOC Feeds To Return" parameter provided as non-positive. Using default value of'
                f" {DEFAULT_MAX_IOC_FEEDS_TO_RETURN}"
            )
            max_ioc_feeds_to_return = DEFAULT_MAX_IOC_FEEDS_TO_RETURN

        manager = FireEyeCMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Listing IOC feeds in {PROVIDER_NAME}")
        ioc_feeds = manager.list_ioc_feeds(limit=max_ioc_feeds_to_return)
        siemplify.LOGGER.info(f"Found {len(ioc_feeds)} IOC Feeds.")

        if ioc_feeds:
            output_message = (
                f"Successfully listed available IOC feeds in {PROVIDER_NAME}!"
            )
            siemplify.result.add_result_json(
                {"customFeedInfo": [ioc_feed.to_json() for ioc_feed in ioc_feeds]}
            )
            siemplify.result.add_data_table(
                title="Available IOC Feeds",
                data_table=construct_csv([ioc_feed.as_csv() for ioc_feed in ioc_feeds]),
            )
            result_value = True
        else:
            output_message = f"No IOC feeds were found in {PROVIDER_NAME}!"

    except Exception as error:
        output_message = f'Error executing action "List IOC Feeds". Reason: {error}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    finally:
        try:
            if manager:
                siemplify.LOGGER.info(f"Logging out from {PROVIDER_NAME}..")
                manager.logout()
                siemplify.LOGGER.info(f"Successfully logged out from {PROVIDER_NAME}")
        except Exception as error:
            siemplify.LOGGER.error(f"Logging out failed. Error: {error}")
            siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
