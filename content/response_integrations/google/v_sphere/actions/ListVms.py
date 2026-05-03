# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.VSphereManager import VSphereManager
import json


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    conf = siemplify.get_configuration("VSphere")
    server_address = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    port = int(conf["Port"])

    # Connect
    vsphere_manager = VSphereManager(server_address, username, password, port)

    vms = vsphere_manager.get_all_vms()
    vms_info = []
    vm_names = []
    for vm in vms:
        vm_names.append(vm.name)
        vms_info.append(VSphereManager.get_vm_info(vm))

    csv_output = VSphereManager.construct_csv(vms_info)

    siemplify.result.add_data_table("Vms Info", csv_output)
    siemplify.result.add_result_json(json.dumps(vms_info))

    siemplify.end(f"Found {len(vms)} vms", json.dumps(vm_names))


if __name__ == "__main__":
    main()
