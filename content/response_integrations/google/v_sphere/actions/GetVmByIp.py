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
