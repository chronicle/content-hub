from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import GET_ASN_TAKEDOWN_REPUTATION_SCRIPT_NAME, INTEGRATION_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = GET_ASN_TAKEDOWN_REPUTATION_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    asn = siemplify.extract_action_param("ASN", print_value=True)
    explain = siemplify.extract_action_param("Explain", print_value=True)
    limit = siemplify.extract_action_param("Limit", print_value=True)
    if explain == "false":
        explanation: int = 0
    else:
        explanation: int = 1

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.get_asn_takedown_reputation(asn, explanation, limit)
        takedown_history = raw_response.get("takedown_reputation")
        if not takedown_history:
            error_message = f"No takedown reputation history found for ASN: {asn}."
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"asn : {takedown_history}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
        siemplify.result.add_result_json({asn: takedown_history})
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve reputation data found for ASN {asn} "
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
