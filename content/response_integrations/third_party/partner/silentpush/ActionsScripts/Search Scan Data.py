from constants import INTEGRATION_NAME, SEARCH_SCAN_DATA_SCRIPT_NAME
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from SilentPushManager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_SCAN_DATA_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    query = siemplify.extract_action_param("query", print_value=True)
    fields = bool(siemplify.extract_action_param("fields", print_value=True))
    limit = siemplify.extract_action_param("limit", print_value=True)
    skip = siemplify.extract_action_param("skip", print_value=True)
    with_metadata = bool(siemplify.extract_action_param("with_metadata", print_value=True))

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.search_scan_data(
            query, limit=limit, fields=fields, skip=skip, with_metadata=with_metadata
        )

        scan_data = raw_response.get("response", {}).get("scandata_raw", [])

        if not scan_data:
            error_message = "No scan data records found"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"records: {scan_data}, query: {query}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve scan data records, for {INTEGRATION_NAME} server! Error: {error}"
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
