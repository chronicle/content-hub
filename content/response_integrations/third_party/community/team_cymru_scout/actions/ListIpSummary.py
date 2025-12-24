from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ApiManager import ApiManager
from ..core.constants import INTEGRATION_NAME, LIST_IPS_SCRIPT_NAME
from ..core.ListSummary import ListSummary
from ..core.TeamCymruScoutException import TeamCymruScoutException
from ..core.utils import (
    create_api_usage_table,
    get_integration_params,
    render_data_table,
)


@output_handler
def main():
    """List IP Summary fetches the details for the provided IPs from Team Cymru Scout."""
    siemplify = SiemplifyAction()

    auth_type, api_key, username, password, verify_ssl = get_integration_params(
        siemplify,
    )

    try:
        ip_summary = ListSummary(siemplify)
        if ip_summary.error:
            raise TeamCymruScoutException(ip_summary.error)

        api_manager = ApiManager(
            auth_type,
            api_key,
            username,
            password,
            siemplify.LOGGER,
            verify_ssl,
        )
        is_success, valid_ips, additional_msg = ip_summary.get_ips_summary(api_manager)

        # Raise error if all the API calls fail, or there are no valid IPs provided
        if not is_success:
            raise TeamCymruScoutException(additional_msg + ip_summary.error)

        status = EXECUTION_STATE_COMPLETED

        if additional_msg:
            siemplify.LOGGER.warning(additional_msg)

        successful_ips = [ip_info["ip"] for ip_info in ip_summary.summary]
        output_message = (
            additional_msg
            + f"Successfully fetched the IP details for the following {is_success} out of "
            f"{len(valid_ips)} valid IPs: {', '.join(successful_ips)} from {INTEGRATION_NAME}.\n"
        )

        # If some API calls fail
        if ip_summary.error:
            siemplify.LOGGER.error(ip_summary.error)
            output_message += ip_summary.error

        siemplify.result.add_result_json(ip_summary.summary)
        ip_summary.generate_tables()

        account_usage = create_api_usage_table(ip_summary.usage)
        render_data_table(siemplify, "Account Usage", account_usage)

    except Exception as e:
        is_success = False
        response = str(e)

        siemplify.LOGGER.error(
            f"General error performing action {LIST_IPS_SCRIPT_NAME}.",
        )
        siemplify.LOGGER.exception(response)

        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to fetch summary information for the given IP Addresses!\nError: {response}"

    result_value = bool(is_success)

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
