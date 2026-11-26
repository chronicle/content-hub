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
from ..core.ProtectwiseManager import ProtectwiseManager
from soar_sdk.SiemplifyUtils import dict_to_flat, convert_datetime_to_unix_time, utc_now
import datetime
import json


@output_handler
def main():
    siemplify = SiemplifyAction()

    configurations = siemplify.get_configuration("Protectwise")
    email = configurations["Email"]
    password = configurations["Password"]

    time_delta = int(siemplify.parameters["Timeframe (hours)"])

    # Get time frame in unixtime
    end_time = utc_now()
    start_time = utc_now() - datetime.timedelta(hours=time_delta)

    end_time = convert_datetime_to_unix_time(end_time)
    start_time = convert_datetime_to_unix_time(start_time)

    protectwise_manager = ProtectwiseManager(email, password)

    entities_with_events = []

    # All events list - for returning events json as result
    all_events = []

    for entity in siemplify.target_entities:
        results = None

        if entity.entity_type == EntityTypes.ADDRESS:
            results = protectwise_manager.get_ip_reputation(
                entity.identifier, start_time, end_time
            )

        if results:
            if results.get("threat") and results["threat"]["events"]["count"]["total"]:
                # There are events - get their data and attach as csv
                entities_with_events.append(entity.identifier)
                events_info = []

                for event in results["threat"]["events"]["top"]:
                    events_info.append(dict_to_flat(event["_original"]))

                all_events.append(events_info)

                csv_output = protectwise_manager.construct_csv(events_info)

                siemplify.result.add_entity_table(entity.identifier, csv_output)

    if entities_with_events:
        output_message = (
            "Successfully found events for the following entities: \n"
            + "\n".join(entities_with_events)
        )
    else:
        output_message = "No events were found."

    siemplify.end(output_message, json.dumps(all_events))


if __name__ == "__main__":
    main()
