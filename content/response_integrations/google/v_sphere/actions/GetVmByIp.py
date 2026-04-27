from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.VSphereManager import VSphereManager
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    conf = siemplify.get_configuration("VSphere")
    server_address = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    port = int(conf["Port"])

    vsphere_manager = VSphereManager(server_address, username, password, port)

    vms = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            vms[entity.identifier] = vsphere_manager.get_vm_info(
                vsphere_manager.get_vm_by_ip(entity.identifier)
            )

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(vms))

    siemplify.end(
        "Vsphere - Found the following vms: \n"
        + "\n".join([f"{ip}: {vm['Name']}" for ip, vm in list(vms.items())]),
        "true",
    )


if __name__ == "__main__":
    main()
