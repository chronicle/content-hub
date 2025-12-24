from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.MicrosoftGraphSecurityManager import MicrosoftGraphSecurityManager


@output_handler
def main():
    siemplify = SiemplifyAction()

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
    user_email = siemplify.extract_action_param("User ID", print_value=True)
    message_id = siemplify.extract_action_param("Message ID", print_value=True)

    siemplify.LOGGER.info("Connecting to Microsoft Graph Security.")
    mtm = MicrosoftGraphSecurityManager(
        client_id,
        secret_id,
        certificate_path,
        certificate_password,
        tenant_id,
    )
    siemplify.LOGGER.info("Connected successfully.")

    request_data = mtm.delete_message(user_email, message_id)

    status = EXECUTION_STATE_COMPLETED
    output_message = request_data["output_message"]
    result_value = "success"
    siemplify.result.add_result_json(request_data)
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
