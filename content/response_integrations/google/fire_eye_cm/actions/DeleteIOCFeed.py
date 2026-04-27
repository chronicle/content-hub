from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.FireEyeCMConstants import PROVIDER_NAME, DELETE_IOC_FEED_SCRIPT_NAME
from ..core.FireEyeCMExceptions import FireEyeCMNotFoundException
from ..core.FireEyeCMManager import FireEyeCMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_IOC_FEED_SCRIPT_NAME

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

    # Init Action Parameters
    feed_name = extract_action_param(
        siemplify, param_name="Feed Name", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    manager = None
    output_message = ""

    try:
        manager = FireEyeCMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        # Check if feed name exists in FireEye CM
        siemplify.LOGGER.info(f"Checking if feed exists in {PROVIDER_NAME}")
        feed_names = [feed.feed_name for feed in manager.list_ioc_feeds()]
        siemplify.LOGGER.info(
            f"Successfully listed {len(feed_names)} IOC feeds in {PROVIDER_NAME}"
        )
        if feed_name not in feed_names:
            raise FireEyeCMNotFoundException(
                f"Failed to check if the feed name exists in {PROVIDER_NAME}"
            )
        siemplify.LOGGER.info(
            f"Feed name {feed_name} found to exist in {PROVIDER_NAME}"
        )

        # Delete IOC feed
        siemplify.LOGGER.info(f"Deleting IOC {feed_name} in {PROVIDER_NAME}")
        manager.delete_ioc_feed(feed_name=feed_name)

        # Check if IOC feed was deleted
        siemplify.LOGGER.info(
            f"Submitted a deletion request. Listing available IOC feeds to check if feed name was deleted."
        )
        feed_ioc_names = [feed.feed_name for feed in manager.list_ioc_feeds()]
        siemplify.LOGGER.info(
            f"Successfully listed IOC feeds. Checking if feed name was deleted."
        )

        if feed_name not in feed_ioc_names:
            output_message = (
                f"Successfully deleted feed {feed_name} in {PROVIDER_NAME}!"
            )
            result_value = True
        else:
            output_message = (
                f"Action wasn't able to delete feed {feed_name} in {PROVIDER_NAME}."
            )

    except FireEyeCMNotFoundException as error:
        output_message = f'Action wasn\'t able to delete IOC feed in {PROVIDER_NAME}. Reason: Feed "{feed_name}" was not found.'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = f'Error executing action "Delete IOC Feed". Reason: {error}'
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
