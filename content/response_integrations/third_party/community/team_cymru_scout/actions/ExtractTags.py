from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ApiManager import ApiManager
from ..core.constants import ERRORS, EXTRACT_TAGS_SCRIPT_NAME, MAX_DAYS, MAX_PAGE_SIZE
from ..core.TeamCymruScoutException import TeamCymruScoutException
from ..core.utils import (
    create_api_usage_table,
    create_tag_list,
    get_integration_params,
    render_data_table,
)
from ..core.validator import is_invalid_ip


def get_ips_matching_with_tags_from_response(
    ip_tags_response: dict[str, set],
    tags_list_to_search: set,
    current_ip: str,
):
    """Given a dictionary of IP address to tags and a list of tags to search,
    return a list of IP addresses where the tags match any of the tags in the list of tags to search.
    """
    matching_tag_ips = set()
    matching_tags = {"current": set(), "peers": set()}

    for ip, tags in list(ip_tags_response.items()):
        match = tags.intersection(tags_list_to_search)
        if match:
            matching_tag_ips.add(ip)
            if ip == current_ip:
                matching_tags["current"] = match
            else:
                matching_tags["peers"] |= match

    return matching_tag_ips, matching_tags


def process_get_ip_details_response(response, current_ip):
    """Process the response from the get_ip_details endpoint of Team Cymru Scout and build the final response with the ip and tags."""
    final_response = {}
    tags = response.get("summary", {}).get("tags", [])
    peers = response.get("communications", {}).get("peers", []) or []

    final_response[current_ip] = set(create_tag_list(tags))

    for peer in peers:
        ip = peer.get("peer", {}).get("ip")
        tags = peer.get("peer", {}).get("tags", [])
        final_response[ip] = set(create_tag_list(tags))

    return final_response


@output_handler
def main():
    """Extract Tags action is used to extract the tags from the JSON response provided by Get IP Details endpoint of Team Cymru Scout
    and search for the given tags in the response, and prepare a list of IPs that match the given tags.

    The action returns a list of IPs that match the given tags as output message.
    """
    siemplify = SiemplifyAction()
    auth_type, api_key, username, password, verify_ssl = get_integration_params(
        siemplify,
    )

    is_success = False

    try:
        tags_to_search = siemplify.extract_action_param(
            "Tags to Search",
            is_mandatory=True,
        ).strip()
        ip_address = siemplify.extract_action_param(
            "IP Address",
            is_mandatory=True,
        ).strip()
        tags_to_search = {tag.strip() for tag in tags_to_search.split(",")}

        params = {
            "start_date": "",
            "end_date": "",
            "days": MAX_DAYS,
            "size": MAX_PAGE_SIZE["IP_DETAILS"],
        }

        if is_invalid_ip(ip_address):
            raise TeamCymruScoutException(
                ERRORS["VALIDATIONS"]["INVALID_IP"].format(ip_address),
            )

        # get ip details api call
        api_manager = ApiManager(
            auth_type,
            api_key,
            username,
            password,
            siemplify.LOGGER,
            verify_ssl,
        )
        is_call_successful, response = api_manager.get_ip_details(ip_address, params)

        if not is_call_successful:
            raise TeamCymruScoutException(response)

        usage = response.get("usage", {})
        current_ip = response.get("ip", "")
        ips_with_tags = process_get_ip_details_response(response, current_ip)

        # Search all the peers tags and prepare matching peers list
        suspicious_ips, matching_tags = get_ips_matching_with_tags_from_response(
            ips_with_tags,
            tags_to_search,
            current_ip,
        )

        output_message = ""
        if suspicious_ips:
            is_success = True
            json_output = {ip: list(ips_with_tags[ip]) for ip in suspicious_ips}
            siemplify.result.add_result_json(json_output)

            if current_ip in suspicious_ips:
                output_message += f"The provided IP contains the tags you specified.\nThe matching tags are: {', '.join(matching_tags['current'])}\n"
                suspicious_ips.remove(current_ip)

            if suspicious_ips:
                output_message += f"{len(suspicious_ips)} peer IPs contain the tags you specified.\nThe matching tags are: {', '.join(matching_tags['peers'])}\n"

        else:
            output_message = "The provided IP and its associated peers do not have any matching tags.\n"

        status = EXECUTION_STATE_COMPLETED

        account_usage = create_api_usage_table(usage)
        render_data_table(siemplify, "Account Usage", account_usage)

    except Exception as error:
        output_message = (
            f"Failed to extract tags for the given IP Address! Error: {error}"
        )

        response = str(error)
        siemplify.LOGGER.error(
            f"Error occurred while performing action: {EXTRACT_TAGS_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(response)
        status = EXECUTION_STATE_FAILED

    finally:
        result_value = is_success
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"Result: {result_value}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
