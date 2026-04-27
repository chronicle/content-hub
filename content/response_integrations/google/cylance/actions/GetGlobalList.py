from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CylanceManager import CylanceManager
from soar_sdk.SiemplifyUtils import dict_to_flat
import json

SCRIPT_NAME = "Cylance - GetGlobalList"


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

    list_type = siemplify.parameters.get("List Type")

    global_list = cm.get_global_list(list_type=list_type)

    if global_list:
        global_list = list(map(dict_to_flat, global_list))
        csv_output = cm.construct_csv(global_list)

        siemplify.result.add_data_table(f"Cylance {list_type}", csv_output)
        output_message = f"Global list {list_type} is attached as a table."

    else:
        output_message = f"Unable to get {list_type}"

    siemplify.result.add_result_json(json.dumps(global_list))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
