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
from soar_sdk.SiemplifySdkConfig import SiemplifySdkConfig
from ..core.WMIManager import WMIManagerBuilder
from soar_sdk.SiemplifyUtils import flat_dict_to_csv, dict_to_flat
import json


@output_handler
def main():
    # NOTICE - This action should be an enrichment action, but a wmi access to
    # the enriched entities is needed.
    # To solve this issue, it must be defined that in order to use this action
    # as an enrichment action, Siemplify user must be granted wmi access to
    # the entities (otherwise the action will fail)

    siemplify = SiemplifyAction()
    server_addr = siemplify.parameters["Server Address"]
    username = siemplify.parameters.get("Username")
    password = siemplify.parameters.get("Password")

    wmi_manager = WMIManagerBuilder.create_manager(
        server_addr, username, password, SiemplifySdkConfig.is_linux()
    )

    info = wmi_manager.get_system_info()

    if info:
        flat_info = dict_to_flat(info)
        csv_output = flat_dict_to_csv(flat_info)
        siemplify.result.add_data_table("WMI System Info", csv_output)

    output_message = "Successfully retrieved system information."
    siemplify.result.add_result_json(json.dumps(info or {}))
    siemplify.end(output_message, json.dumps(info))


if __name__ == "__main__":
    main()
