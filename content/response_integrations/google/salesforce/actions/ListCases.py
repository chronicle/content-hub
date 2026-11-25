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

from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.SalesforceManager import SalesforceManager, SalesforceManagerError, parse_max_records


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("Salesforce")
    server_addr = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]
    token = configurations["Token"]
    verify_ssl = configurations.get("Verify SSL", "False").lower() == "true"

    try:
        max_records = parse_max_records(siemplify.parameters.get("Max Records To Return"))
    except SalesforceManagerError as err:
        siemplify.end(f'Error executing action "List Cases". Reason: {err}', "false", EXECUTION_STATE_FAILED)
        return

    salesforce_manager = SalesforceManager(username, password, token, server_addr=server_addr, verify_ssl=verify_ssl)

    cases = salesforce_manager.get_cases(max_records=max_records)

    if cases:
        csv_output = construct_csv(cases)
        siemplify.result.add_data_table("Cases", csv_output)

    siemplify.result.add_result_json(cases)
    siemplify.end(f"Found {len(cases)} cases.", "true")


if __name__ == "__main__":
    main()
