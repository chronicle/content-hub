from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import GET_IPV4_REPUTATION_SCRIPT_NAME, INTEGRATION_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = GET_IPV4_REPUTATION_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    nameserver = siemplify.extract_action_param("Nameserver", print_value=True)
    explain = siemplify.extract_action_param("Explain", print_value=True)
    limit = siemplify.extract_action_param("Limit", print_value=True)
    if explain == "false":
        explaination: bool = False
    else:
        explaination: bool = True
    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.get_ipv4_reputation(nameserver, explaination, limit)

        history = raw_response.get("ip_reputation_history", {})

        if not history:
            error_message = f"No reputation data found for IPv4: {nameserver}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)
        siemplify.result.add_result_json({"Response": raw_response})
        output_message = f"Response : {raw_response}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve reputation data found for IPv4: {nameserver} "
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
