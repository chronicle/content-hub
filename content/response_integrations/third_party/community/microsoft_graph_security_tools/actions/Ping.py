from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.MicrosoftGraphSecurityManager import MicrosoftGraphSecurityManager

INTEGRATION_NAME = "MicrosoftGraphSecurity"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    client_id = siemplify.extract_configuration_param("Integration", "Client ID")
    secret_id = siemplify.extract_configuration_param("Integration", "Secret ID")
    tenant_id = siemplify.extract_configuration_param("Integration", "Tenant ID")
    certificate_password = siemplify.extract_configuration_param(
        "Integration",
        "Certificate Password",
    )
    certificate_path = siemplify.extract_configuration_param(
        "Integration",
        "Certificate Path",
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info("Connecting to Microsoft Graph Security.")
        mtm = MicrosoftGraphSecurityManager(
            client_id,
            secret_id,
            certificate_path,
            certificate_password,
            tenant_id,
        )
        siemplify.LOGGER.info("Connected successfully.")

        output_message = "Connection Established"
        result_value = "true"
        status = EXECUTION_STATE_COMPLETED

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
