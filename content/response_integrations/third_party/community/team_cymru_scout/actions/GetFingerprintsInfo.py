from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ApiManager import ApiManager
from ..core.constants import GET_FINGERPRINTS_INFO_SCRIPT_NAME, INTEGRATION_NAME
from ..core.IPInfoSection import IPInfoSection
from ..core.TeamCymruScoutException import TeamCymruScoutException
from ..core.utils import (
    create_api_usage_table,
    get_integration_params,
    render_data_table,
)


@output_handler
def main():
    """Get Fingerprints Info action is used to fetch the Fingerprints information for the given IP Address from Team Cymru Scout."""
    siemplify = SiemplifyAction()

    auth_type, api_key, username, password, verify_ssl = get_integration_params(
        siemplify,
    )

    try:
        ip_info = IPInfoSection(siemplify, section="fingerprints")

        if ip_info.error:
            raise TeamCymruScoutException(ip_info.error)

        api_manager = ApiManager(
            auth_type,
            api_key,
            username,
            password,
            siemplify.LOGGER,
            verify_ssl,
        )
        is_success, response, valid_ips, additional_msg, usage = ip_info.get_ip_details(
            api_manager,
        )

        if not is_success:
            raise TeamCymruScoutException(additional_msg + ip_info.error)

        status = EXECUTION_STATE_COMPLETED

        if additional_msg:
            siemplify.LOGGER.warning(additional_msg)

        successful_ips = ", ".join(list(response.keys()))
        output_message = (
            additional_msg
            + f"Successfully fetched the Fingerprints Information for the following {is_success} out of {len(valid_ips)} valid IPs: {successful_ips} from {INTEGRATION_NAME}.\n\n"
        )

        # If some API calls fail
        if ip_info.error:
            siemplify.LOGGER.error(ip_info.error)
            output_message += ip_info.error

        siemplify.result.add_result_json(response)
        ip_info.generate_tables()

        account_usage = create_api_usage_table(usage)
        render_data_table(siemplify, "Account Usage", account_usage)

    except Exception as e:
        is_success = False
        response = str(e)
        siemplify.LOGGER.error(
            f"General error performing action {GET_FINGERPRINTS_INFO_SCRIPT_NAME}.",
        )
        siemplify.LOGGER.exception(response)

        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to fetch Fingerprints information\nError: {response}"

    result_value = bool(is_success)

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
