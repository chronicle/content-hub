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

    file_list_name = siemplify.parameters["File List Name"]

    file_list = cisco_amp_manager.get_file_list_by_name(file_list_name) or {}

    if file_list.get("items"):
        flat_items = []

        for item in file_list.get("items"):
            # Remove links - irrelevant
            if item.get("links"):
                del item["links"]
            flat_items.append(dict_to_flat(item))

        # Attach file lists in csv
        csv_output = construct_csv(flat_items)
        siemplify.result.add_data_table(f"Items - {file_list_name}", csv_output)

    siemplify.result.add_result_json(file_list)

    siemplify.end(
        f"Successfully found {len(file_list.get('items', []))} items in {file_list_name}.",
        json.dumps(file_list.get("items")),
    )


if __name__ == "__main__":
    main()
