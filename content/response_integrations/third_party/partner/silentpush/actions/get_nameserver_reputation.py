from datetime import datetime

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import GET_NAMESERVER_REPUTATION_SCRIPT_NAME, INTEGRATION_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_NAMESERVER_REPUTATION_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    nameserver = siemplify.extract_action_param("Nameserver", print_value=True)
    explain = siemplify.extract_action_param("Explain", print_value=True)
    limit = siemplify.extract_action_param("Limit", print_value=True)

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        reputation_data = sp_manager.get_nameserver_reputation(nameserver, explain, limit)

        if not isinstance(reputation_data, list):
            siemplify.LOGGER.error(f"Expected list, got: {type(reputation_data)}")
            reputation_data = []

        for item in reputation_data:
            date_val = item.get("date")
            if isinstance(date_val, int):
                try:
                    parsed_date = datetime.strptime(str(date_val), "%Y%m%d").date()
                    item["date"] = parsed_date.isoformat()
                except ValueError as e:
                    siemplify.LOGGER.error(f"Failed to parse date {date_val}: {e}")

        if not reputation_data:
            error_message = f"No valid reputation history found for nameserver: {nameserver}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"nameserver: {nameserver}, reputation_data: {reputation_data}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve nameserver reputation :{nameserver} "
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
