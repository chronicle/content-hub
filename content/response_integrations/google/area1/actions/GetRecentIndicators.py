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
from ..core.Area1Manager import Area1Manager
import arrow
import json

ACTION_NAME = "Area1_Get Recent Indicators"
INDICATORS_TABLE_HEADER = "Recent Indicators"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    configurations = siemplify.get_configuration("Area1")
    server_addr = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]
    verify_ssl = configurations.get("Verify SSL", "false").lower() == "true"

    area1_manager = Area1Manager(server_addr, username, password, verify_ssl)

    seconds_back = int(siemplify.parameters.get("Seconds Back", 60))

    indicators = area1_manager.get_recent_indicators(
        since=arrow.utcnow().timestamp - seconds_back
    )

    if indicators:
        output_message = (
            f"Found {len(indicators)} indicators {seconds_back} seconds back."
        )
        indicators_csv = construct_csv(list(map(dict_to_flat, indicators)))
        siemplify.result.add_data_table(INDICATORS_TABLE_HEADER, indicators_csv)
    else:
        output_message = f"No indicators where found {seconds_back} seconds back."

    siemplify.result.add_result_json(json.dumps(indicators))
    siemplify.end(output_message, json.dumps(indicators))


if __name__ == "__main__":
    main()
