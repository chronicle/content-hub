from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.VSphereManager import VSphereManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    conf = siemplify.get_configuration("VSphere")
    server_address = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    port = int(conf["Port"])

    vm_name = siemplify.parameters["Vm Name"]

    # Connect
    vsphere_manager = VSphereManager(server_address, username, password, port)

    # Power on vm
    vm = vsphere_manager.get_obj_by_name(vm_name)
    vsphere_manager.suspend_vm(vm)

    siemplify.end(f"Successfully suspended {vm.name}", "true")


if __name__ == "__main__":
    main()
