from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NessusScannerManager import NessusScanner

# Consts
ADDRESS = EntityTypes.ADDRESS
HOSTNAME = EntityTypes.HOSTNAME


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("NessusScanner")
    access_key = conf["Access Key"]
    secret_key = conf["Secret Key"]
    server_address = conf["Api Root"]
    nessus_client = NessusScanner(access_key, secret_key, server_address)

    # Parameters
    scan_name = siemplify.parameters["Scan Name"]
    description = siemplify.parameters.get("Description", "Created by Rest API")
    template_title = siemplify.parameters["Scan Template Title"]

    # Form Scan Targets.
    scan_targets = [
        entity.identifier
        for entity in siemplify.target_entities
        if entity.entity_type == ADDRESS or entity.entity_type == HOSTNAME
    ]

    json_results = {}
    # Adjust to Nessus target format
    scan_targets = ",".join(scan_targets)
    # Get template id by template title:
    template_id = nessus_client.get_scan_template_uuid_by_title(template_title)
    # Create new scan
    new_scan = nessus_client.create_scan(
        scan_name, scan_targets, description, template_id
    )

    if new_scan:
        json_results = new_scan
        output_message = f"Successfully create {scan_name} scan."
        result_value = "true"
    else:
        output_message = f"Failed to create {scan_name} scan."
        result_value = "false"

    siemplify.result.add_result_json(json_results)

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
