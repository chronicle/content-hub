from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from connect_wise.core.ConnectWiseManager import ConnectWiseManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED


INTEGRATION_NAME = "ConnectWise"
ATTACHMENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Attachment To Ticket"


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    company_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    company_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Company Name",
        is_mandatory=True,
        print_value=True,
    )
    public_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Public Key",
        is_mandatory=True,
        print_value=True,
    )
    private_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Private Key",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Id",
        is_mandatory=True,
        print_value=True,
    )

    ticket_id = extract_action_param(
        siemplify, param_name="Ticket ID", is_mandatory=True, print_value=True
    )
    base64_encoded_file = extract_action_param(
        siemplify,
        param_name="Base64 Encoded File",
        is_mandatory=True,
        print_value=False,
    )
    filename = extract_action_param(
        siemplify, param_name="Filename", is_mandatory=True, print_value=True
    )
    display_in_customer_portal = extract_action_param(
        siemplify,
        param_name="Display In Customer Portal",
        print_value=True,
        input_type=bool,
    )
    allow_only_owner_update = extract_action_param(
        siemplify,
        param_name="Allow Only Owner Update",
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        validate_filename(filename=filename)

        manager = ConnectWiseManager(
            company_url, company_name, public_key, private_key, client_id
        )

        result = manager.add_attachment_to_ticket(
            ticket_id,
            base64_encoded_file,
            filename,
            display_in_customer_portal,
            allow_only_owner_update,
        )

        output_message = f"Successfully added a file as attachment to ticket {ticket_id} in ConnectWise."
        siemplify.result.add_result_json(result.to_json())

    except Exception as e:
        output_message = (
            f"Error executing action {ATTACHMENT_SCRIPT_NAME}. Reason: {e} "
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


def validate_filename(filename):
    try:
        name_extension = filename.split(".")
        # File does not have extension
        if len(name_extension) == 1:
            raise
    except Exception as e:
        raise Exception(
            '"Filename" value doesn\'t follow the needed format: Format: {filename}.{extension}'
        )


if __name__ == "__main__":
    main()
