from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from SilentPushManager import RESOURCE, SilentPushManager
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import GET_ENRICHMENT_DATA_SCRIPT_NAME, INTEGRATION_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ENRICHMENT_DATA_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Silent Push Server"
    )
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    resource = siemplify.extract_action_param("resource", print_value=True)
    value = siemplify.extract_action_param("value", print_value=True)
    explain = siemplify.extract_action_param("explain", print_value=True)
    scan_data = siemplify.extract_action_param("scan_data", print_value=True)
    if explain == "false":
        explanation: bool = False
    else:
        explanation: bool = True

    if scan_data == "false":
        scan_data_val: bool = False
    else:
        scan_data_val: bool = True
    if resource not in RESOURCE:
        raise ValueError(f"Invalid input: {resource}. Allowed values are {RESOURCE}")

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)

        if resource in ["ipv4", "ipv6"]:
            validate_ip(sp_manager, resource, value)

        enrichment_data = sp_manager.get_enrichment_data(
            resource, value, explanation, scan_data_val
        )

        if not enrichment_data:
            error_message = f"No enrichment data found for resource: {value}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"value: {value}, {enrichment_data}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
        siemplify.result.add_result_json({value: enrichment_data})
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve enrichment data found for resource: "
            f"{value} for {INTEGRATION_NAME} server! Error: {error}"
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


def validate_ip(client: SilentPushManager, resource: str, value: str) -> None:
    """
    Validate the IP address based on the resource type.

    Args:
        client (Client): The client object to interact with the enrichment service.
        resource (str): The resource type (ipv4 or ipv6).
        value (str): The IP address to validate.

    Raises:
        ValueError: If the IP address is invalid for the given resource type.
    """
    is_valid_ip = client.validate_ip_address(value, allow_ipv6=(resource == "ipv6"))
    if not is_valid_ip:
        raise ValueError(f"Invalid {resource.upper()} address: {value}")


if __name__ == "__main__":
    main()
