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
from ..core.CyberarkVaultManager import CyberarkManager
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("CyberArkVault")
    username = conf["Username"]
    password = conf["Password"]
    use_ssl = conf["Use SSL"]
    api_root = conf["Api Root"]

    cyberark_manager = CyberarkManager(username, password, api_root, use_ssl)

    group_name = siemplify.parameters["Group Name"]

    group_details = cyberark_manager.get_group_details(group_name)
    if group_details:
        flat_report = dict_to_flat(group_details)
        siemplify.result.add_data_table(
            f"{group_name} Details:", flat_dict_to_csv(flat_report)
        )
        output_message = "Attached group details."
        result_value = "true"
    else:
        output_message = "Group not found."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
