from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param

from core.constants import (
    GET_ADMINISTRATOR_CONSENT_SCRIPT_NAME,
    INTEGRATION_NAME,
    URL_AUTHORIZATION,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ADMINISTRATOR_CONSENT_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant",
        is_mandatory=True,
        input_type=str,
    )
    redirect_uri = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Redirect URL",
        default_value=False,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info("Generating authorization link.")
        url = URL_AUTHORIZATION.format(
            tenant=tenant, client_id=client_id, redirect_uri=redirect_uri
        )

        if url:
            siemplify.result.add_link("Browse to this authorization link", url)
            siemplify.LOGGER.info(f"Successfully generated link: {url}")
            status = EXECUTION_STATE_COMPLETED
        else:
            siemplify.LOGGER.error("Failed to create an authorization url")
            status = EXECUTION_STATE_FAILED

        output_message = (
            "Your browser should be redirected with a response in the address bar. If the administrator"
            " approves the permissions for your application, admin_consent set to True."
            if url
            else "Failed to create an authorization url"
        )

        result_value = "true" if url else "false"

    except Exception as e:
        siemplify.LOGGER.error(f"Some errors occurred. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Some errors occurred. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
