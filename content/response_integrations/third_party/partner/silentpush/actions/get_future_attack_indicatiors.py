from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import GET_FUTURE_ATTACK_INDICATORS_SCRIPT_NAME, INTEGRATION_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = GET_FUTURE_ATTACK_INDICATORS_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Silent Push Server"
    )
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    feed_uuid = siemplify.extract_action_param("Feed UUID", print_value=True)
    page_no = siemplify.extract_action_param("Page No", print_value=True)
    page_size = siemplify.extract_action_param("Page Size", print_value=True)

    if page_no is None:
        page_no = 1
    if page_size is None:
        page_size = 10000

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.get_future_attack_indicators(
            feed_uuid, page_no, page_size
        )

        # Handle list or dict gracefully
        if isinstance(raw_response, list):
            indicators = raw_response
        else:
            indicators = raw_response.get("indicators", [])

        if not indicators:
            error_message = f"No data found for feed_uuid {feed_uuid}."
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"Result : {indicators}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
        siemplify.result.add_result_json({"Output": indicators})
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve data for feed_uuid {feed_uuid}, "
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
