from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv
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

    cases = salesforce_manager.get_cases()

    csv_output = construct_csv(cases)
    siemplify.result.add_data_table("Cases", csv_output)

    siemplify.result.add_result_json(cases)
    siemplify.end(f"Found {len(cases)} cases.", "true")


if __name__ == "__main__":
    main()
