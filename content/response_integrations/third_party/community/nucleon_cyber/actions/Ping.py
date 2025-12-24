from __future__ import annotations

import requests
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME = "NucleonCyber - integration - v1"

SCRIPT_NAME = "NucleonCyber API Ping"
CLIENT_NAME = "usrn"
CLIENT_ID = "clientID"
LIMIT = "limit"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    basic_user = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Username",
    )
    basic_pass = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Password",
    )
    client_name = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="client name",
    )
    client_id = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="client id",
    )
    limit = siemplify.extract_action_param(param_name="limit")

    url = "https://api.nucleoncyber.com/feed/activethreats"

    response = requests.post(
        url=url,
        auth=(basic_user, basic_pass),
        data={CLIENT_NAME: client_name, CLIENT_ID: client_id, LIMIT: limit},
    )

    if response.status_code != 200:
        raise Exception("Error, bad credentials")

    siemplify.end("Successful Connection", True)


if __name__ == "__main__":
    main()
