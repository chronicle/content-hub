from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TenableManager import TenableSecurityCenterManager

SCRIPT_NAME = "TenableSecurityCenter - ScanIps"


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

    scan_name = siemplify.parameters["Scan Name"]
    policy_name = siemplify.parameters["Policy Name"]

    tenable_manager = TenableSecurityCenterManager(
        server_address,
        username,
        password,
        access_key,
        secret_key,
        use_ssl,
    )

    scan_list = []

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            scan_list.append(entity.identifier)

    if scan_list:
        scan_result_id = tenable_manager.create_and_launch_scan_by_policy_name(
            scan_name, policy_name, scan_list, wait_for_results=False
        )

        output_message = (
            f"Tenable: Initiated scan {scan_result_id} of the following IPs:\n"
            + "\n".join(scan_list)
        )
        result_value = scan_result_id

    else:

        output_message = "Tenable: No IPs to scan."
        result_value = ""

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
