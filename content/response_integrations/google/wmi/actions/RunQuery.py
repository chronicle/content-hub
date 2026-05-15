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
from soar_sdk.SiemplifySdkConfig import SiemplifySdkConfig
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.WMIManager import WMIManagerBuilder
import json


@output_handler
def main():
    siemplify = SiemplifyAction()
    server_addr = siemplify.parameters["Server Address"]
    username = siemplify.parameters.get("Username")
    password = siemplify.parameters.get("Password")
    query = siemplify.parameters["WQL Query"]

    wmi_manager = WMIManagerBuilder.create_manager(
        server_addr, username, password, SiemplifySdkConfig.is_linux()
    )

    items = wmi_manager.run_query(query)
    siemplify.result.add_result_json(json.dumps(items or []))

    if items:
        csv_output = wmi_manager.construct_csv(items)
        siemplify.result.add_data_table("WMI Query Results", csv_output)

        output_message = "Successfully ran query."
        siemplify.end(output_message, json.dumps(items))

    else:
        output_message = "No results from query."
        siemplify.end(output_message, "false")


if __name__ == "__main__":
    main()
