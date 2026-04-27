from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ZendeskManager import ZendeskManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Zendesk")
    user_email = conf["User Email Address"]
    api_token = conf["Api Token"]
    server_address = conf["Server Address"]
    zendesk = ZendeskManager(user_email, api_token, server_address)

    # Execute Test Connectivity.
    result = zendesk.test_connectivity()

    if result:
        output_message = "Connection Established."
        result_value = "true"
    else:
        output_message = "Connection Failed."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
