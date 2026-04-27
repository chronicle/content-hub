from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat
from ..core.CylanceManager import CylanceManager
import json

SCRIPT_NAME = "Cylance - GetThreats"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Cylance")

    server_address = conf["Server Address"]
    application_secret = conf["Application Secret"]
    application_id = conf["Application ID"]
    tenant_identifier = conf["Tenant Identifier"]

    cm = CylanceManager(
        server_address, application_id, application_secret, tenant_identifier
    )

    threats = cm.get_threats()

    if threats:
        threats = list(map(dict_to_flat, threats))
        csv_output = cm.construct_csv(threats)

        siemplify.result.add_data_table("Cylance Threats", csv_output)

    siemplify.result.add_result_json(json.dumps(threats))
    siemplify.end(f"Found {len(threats)} threats.", "true")


if __name__ == "__main__":
    main()
