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
from ..core.SymantecICDXManager import SymantecICDXManager
from soar_sdk.SiemplifyUtils import dict_to_flat, construct_csv
import arrow

PROVIDER = "SymantecICDX"
ACTION_NAME = "SymantecICDX - Get Events Minutes Back"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.action_definition_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)
    verify_ssl = conf.get("Verify SSL").lower() == "true"
    icdx_manager = SymantecICDXManager(
        api_root=conf.get("Api Root"),
        api_key=conf.get("Api Token"),
        verify_ssl=verify_ssl,
    )

    query = siemplify.parameters.get("Query")
    limit = int(siemplify.parameters.get("Limit", 10))
    minutes_back = int(siemplify.parameters.get("Minutes Back", 60))
    fields = siemplify.parameters.get("Fields")

    time_milliseconds = arrow.utcnow().shift(minutes=-minutes_back).timestamp * 1000

    if fields:
        fields = fields.split(",")
        events = icdx_manager.find_events(
            query=query, limit=limit, start_time=time_milliseconds, fields=fields
        )

    else:
        events = icdx_manager.find_events(
            query=query, limit=limit, start_time=time_milliseconds
        )

    if events:
        siemplify.result.add_result_json(events)
        siemplify.result.add_data_table(
            query, construct_csv(list(map(dict_to_flat, events)))
        )
        output_message = f"Found {len(events)} events"
    else:
        output_message = f"No events were found."

    siemplify.end(output_message, len(events))


if __name__ == "__main__":
    main()
