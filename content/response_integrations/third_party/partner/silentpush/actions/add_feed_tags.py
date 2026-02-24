from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import ADD_FEED_TAGS_SCRIPT_NAME, INTEGRATION_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = ADD_FEED_TAGS_SCRIPT_NAME

    server_url = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Silent Push Server"
    )
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    feed_uuid = siemplify.extract_action_param("Feed UUID", print_value=True)
    tags = siemplify.extract_action_param("Tags", print_value=True)
    asn = siemplify.extract_action_param("ASN", print_value=True)

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        result = sp_manager.add_feed_tags(feed_uuid=feed_uuid, tags=tags)

        if not result:
            error_message = f"No data found for feed_uuid {feed_uuid}."
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"{feed_uuid} : {result}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve data found for ASN {asn} "
            f"for {INTEGRATION_NAME} server! Error: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    for entity in siemplify.target_entities:
        print(entity.identifier)

    siemplify.LOGGER.info(
        "\n  status: {}\n  result_value: {}\n  output_message: {}".format(
            status, result_value, output_message
        )
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
