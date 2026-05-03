from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SalesforceManager import SalesforceManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("Salesforce")
    server_addr = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]
    token = configurations["Token"]
    verify_ssl = configurations.get("Verify SSL", "False").lower() == "true"

    salesforce_manager = SalesforceManager(
        username, password, token, server_addr=server_addr, verify_ssl=verify_ssl
    )

    case_number = siemplify.parameters.get("Case Number")
    title = siemplify.parameters.get("Title")
    body = siemplify.parameters.get("Body")

    case = salesforce_manager.get_case_by_number(case_number)

    salesforce_manager.add_comment(case.get("Id"), title, body)

    output_message = f"Successfully added comment to case {case_number}."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
