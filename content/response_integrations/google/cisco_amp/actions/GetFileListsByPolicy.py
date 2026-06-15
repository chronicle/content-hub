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
from soar_sdk.SiemplifyUtils import dict_to_flat, construct_csv
from ..core.CiscoAMPManager import CiscoAMPManager
import json


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("CiscoAMP")
    server_addr = configurations["Api Root"]
    client_id = configurations["Client ID"]
    api_key = configurations["Api Key"]
    use_ssl = configurations["Use SSL"].lower() == "true"

    cisco_amp_manager = CiscoAMPManager(server_addr, client_id, api_key, use_ssl)

    policy_name = siemplify.parameters["Policy Name"]

    policy_info = cisco_amp_manager.get_policy_by_name(policy_name)
    json_results = {}

    if policy_info.get("file_lists"):
        flat_file_lists = []

        for index, file_list in enumerate(policy_info.get("file_lists")):
            # Remove links - irrelevant
            if file_list.get("links"):
                del file_list["links"]

            flat_file_lists.append(dict_to_flat(file_list))
            json_results[index] = file_list

        # Attach file lists in csv
        csv_output = construct_csv(flat_file_lists)
        siemplify.result.add_data_table("File Lists", csv_output)

    siemplify.result.add_result_json(json_results)

    siemplify.end(
        f"Successfully found {len(policy_info.get('file_lists', []))} file lists.",
        json.dumps(policy_info.get("file_lists")),
    )


if __name__ == "__main__":
    main()
