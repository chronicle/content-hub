from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SEPManager import SEP14Manager
from TIPCommon import extract_configuration_param
import json


INTEGRATION_NAME = "SEP"


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("SEP")
    username = conf["Username"]
    password = conf["Password"]
    domain = conf["Domain"]
    url = conf["Api Root"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )
    command_ids = (
        siemplify.parameters.get("Command IDS", "").split(",")
        if siemplify.parameters.get("Command IDS")
        else []
    )

    sep_manager = SEP14Manager(url, username, password, domain, verify_ssl=verify_ssl)

    reports = []

    for command_id in command_ids:
        report = sep_manager.commandStatusReport(command_id)
        if report:
            siemplify.result.add_json(command_id, json.dumps(report))
            reports.append(report)

    output_message = (
        f"Successfully retrieved status report for commands {', '.join(command_ids)}"
    )

    siemplify.result.add_result_json(reports)
    siemplify.end(output_message, json.dumps(reports))


if __name__ == "__main__":
    main()
