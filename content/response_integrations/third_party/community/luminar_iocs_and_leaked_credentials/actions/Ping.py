from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.LuminarManager import LuminarManager


@output_handler
def main():
    """Testing given API Credentials"""
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    client_id = siemplify.extract_configuration_param(
        "Luminar IOCs and Leaked Credentials",
        "Luminar API Client ID",
    )
    client_secret = siemplify.extract_configuration_param(
        "Luminar IOCs and Leaked Credentials",
        "Luminar API Client Secret",
    )
    account_id = siemplify.extract_configuration_param(
        "Luminar IOCs and Leaked Credentials",
        "Luminar API Account ID",
    )
    base_url = siemplify.extract_configuration_param(
        "Luminar IOCs and Leaked Credentials",
        "Luminar Base URL",
    )
    try:
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        return_value, output_message, status = LuminarManager(
            siemplify,
            client_id,
            client_secret,
            account_id,
            base_url,
        ).test_connectivity()
    except Exception as err:
        output_message = f"Failed to connect to Luminar API... Error is {err}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        status = EXECUTION_STATE_FAILED
        return_value = False
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {return_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    main()
