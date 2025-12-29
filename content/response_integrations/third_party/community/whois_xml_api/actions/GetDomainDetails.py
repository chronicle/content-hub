from __future__ import annotations

import requests
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

# Example Consts:
INTEGRATION_NAME = "Whois XML API"

SCRIPT_NAME = "WHOIS XML API GetDomainDetails"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
    )

    url = f"https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey={api_key}&outputFormat=json"

    domain = siemplify.extract_action_param(param_name="Domain Name", print_value=True)
    availabilty_check = siemplify.extract_action_param(
        param_name="Check availability",
        is_mandatory=False,
        print_value=True,
    )

    # Add domain to scan
    url = f"{url}&domainName={domain}"

    # Determine availabilty check
    if availabilty_check.lower() == "true":
        availabilty_check_qs = 1
    else:
        availabilty_check_qs = 0

    url = f"{url}&da={availabilty_check_qs}"

    response = requests.get(url)
    response.raise_for_status()

    # Add a Json result that can be used in the next steps of the playbook.
    siemplify.result.add_result_json(response.json())
    # Add the Json to the action result presented in the context details.
    siemplify.result.add_json("WhoisDetails", response.json())

    msg = f"Fetched data for {domain}"

    siemplify.end(msg, None)


if __name__ == "__main__":
    main()
