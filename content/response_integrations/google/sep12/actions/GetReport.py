from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SEP12Manager import SymantecEp12
import json
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "SEP12"


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("SEP12")
    client_id = conf["Client ID"]
    client_secret = conf["Client Secret"]
    refresh_token = conf["Refresh Token"]
    root_url = conf["Api Root"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )
    # Parameters.
    command_id = siemplify.parameters.get("Command ID")

    sep_manager = SymantecEp12(
        root_url, client_id, client_secret, refresh_token, verify_ssl
    )

    sep_manager.connect()

    report = sep_manager.commandStatusReport(command_id)

    if report:
        siemplify.result.add_json("Report", json.dumps(report))

    output_message = f"Successfully retrieved status report for command {command_id}"

    siemplify.result.add_result_json(report)
    siemplify.end(output_message, json.dumps(report))


if __name__ == "__main__":
    main()
