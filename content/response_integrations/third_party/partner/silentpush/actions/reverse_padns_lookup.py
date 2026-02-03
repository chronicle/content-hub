from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, REVERSE_PADNS_LOOKUP_SCRIPT_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.script_name = REVERSE_PADNS_LOOKUP_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Silent Push Server"
    )
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    qtype = siemplify.extract_action_param("Qtype", print_value=True)
    qname = siemplify.extract_action_param("Qname", print_value=True)
    netmask = siemplify.extract_action_param("Netmask", print_value=True)
    subdomains = siemplify.extract_action_param("Subdomains", print_value=True)
    regex = siemplify.extract_action_param("Regex", print_value=True)
    match_arg = siemplify.extract_action_param("Match", print_value=True)
    first_seen_after = siemplify.extract_action_param("First Seen After", print_value=True
    )
    first_seen_before = siemplify.extract_action_param("First Seen Before", print_value=True
    )
    last_seen_after = siemplify.extract_action_param("Last Seen After", print_value=True
    )
    last_seen_before = siemplify.extract_action_param("Last Seen Before", print_value=True
    )
    as_of = siemplify.extract_action_param("As Of", print_value=True)
    sort = siemplify.extract_action_param("Sort", print_value=True)
    output_format = siemplify.extract_action_param("Output Format", print_value=True)
    prefer = siemplify.extract_action_param("Prefer", print_value=True)
    with_metadata = siemplify.extract_action_param("With Metadata", print_value=True)
    max_wait = siemplify.extract_action_param("Max Wait", print_value=True)
    limit = siemplify.extract_action_param("Limit", print_value=True)
    skip = siemplify.extract_action_param("Skip", print_value=True)

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.reverse_padns_lookup(
            qtype=qtype,
            qname=qname,
            netmask=netmask,
            subdomains=subdomains,
            regex=regex,
            match=match_arg,
            first_seen_after=first_seen_after,
            first_seen_before=first_seen_before,
            last_seen_after=last_seen_after,
            last_seen_before=last_seen_before,
            as_of=as_of,
            sort=sort,
            output_format=output_format,
            prefer=prefer,
            with_metadata=with_metadata,
            max_wait=max_wait,
            skip=skip,
            limit=limit,
        )

        # Check for API error in the response
        if raw_response.get("error"):
            raise ValueError(f"API Error: {raw_response.get('error')}")

        records = raw_response.get("response", {}).get("records", [])

        if not records:
            error_message = f"No records found for {qtype} {qname}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"qtype: {qtype}, qname: {qname}, records: {records}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve data for {INTEGRATION_NAME} server! Error: {error}"
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
