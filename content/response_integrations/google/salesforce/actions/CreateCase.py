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

    subject = siemplify.parameters.get("Subject")
    status = siemplify.parameters.get("Status")
    description = siemplify.parameters.get("Description")
    origin = siemplify.parameters.get("Origin")
    priority = siemplify.parameters.get("Priority")
    case_type = siemplify.parameters.get("Type")

    case = salesforce_manager.create_case(
        subject=subject,
        status=status,
        description=description,
        origin=origin,
        priority=priority,
        case_type=case_type,
    )

    output_message = f"Successfully created case {case.get('CaseNumber')}."

    siemplify.end(output_message, case.get("CaseNumber"))


if __name__ == "__main__":
    main()
