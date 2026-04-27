from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TenableManager import TenableSecurityCenterManager
from soar_sdk.SiemplifyUtils import flat_dict_to_csv
import json

SCRIPT_NAME = "TenableSecurityCenter - GetResults"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("TenableSecurityCenter")
    server_address = conf["Server Address"]
    username = conf.get("Username")
    password = conf.get("Password")
    access_key = conf.get("Access Key")
    secret_key = conf.get("Secret Key")
    use_ssl = conf["Use SSL"].lower() == "true"

    scan_result_id = siemplify.parameters["Scan Result ID"]

    tenable_manager = TenableSecurityCenterManager(
        server_address,
        username,
        password,
        access_key,
        secret_key,
        use_ssl,
    )

    results = tenable_manager.wait_for_scan_results(scan_result_id)

    json_results = {}

    if results:
        csv_output = tenable_manager.construct_csv(results)
        siemplify.result.add_data_table("Tenable Scan Results", csv_output)

        severity_summary = tenable_manager.get_severity_summary(scan_result_id)

        json_results["results"] = results
        json_results["severity_summary"] = severity_summary

        severities = {}

        if severity_summary:
            for severity in severity_summary:
                severities[severity["severity"]["name"]] = severity["count"]

        csv_output = flat_dict_to_csv(severities)
        siemplify.result.add_data_table("Tenable Severity Summary", csv_output)

        output_message = "Tenable: Scan results were attached."
        result_value = "true"

    else:
        output_message = "Tenable: No results were found."
        result_value = "false"

    siemplify.result.add_result_json(json.dumps(json_results))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
