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
from ..core.McAfeeActiveResponseManager import McAfeeActiveResponseManager
from soar_sdk.SiemplifyUtils import construct_csv, dict_to_flat

PROVIDER = "McAfeeActiveResponse"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "McAfeeActiveResponse - Search"
    conf = siemplify.get_configuration(PROVIDER)
    item_results = []

    mar_manager = McAfeeActiveResponseManager(
        conf.get("Broker URLs List").split(",") if conf.get("Broker URLs List") else [],
        conf.get("Broker CA Bundle File Path"),
        conf.get("Certificate File Path"),
        conf.get("Private Key File Path"),
    )

    result_value = False

    # Parameters.
    collectors = (
        siemplify.parameters.get("Collectors").split(",")
        if siemplify.parameters.get("Collectors")
        else []
    )
    filter_collector = siemplify.parameters.get("Filter Collector")
    filter_by = siemplify.parameters.get("Filter By")
    filter_operator = siemplify.parameters.get("Filter Operator")
    filter_value = siemplify.parameters.get("Filter Value")

    result = mar_manager.search_multiple_collectors(
        collectors, filter_collector, filter_by, filter_operator, filter_value
    )

    if result:
        try:
            siemplify.result.add_result_json(result)

            for item in result.get("items", []):
                temp_data = dict_to_flat(item.get("output", {}))
                temp_data["Count"] = item.get("count")
                temp_data["ID"] = item.get("id")
                temp_data["Created At"] = item.get("created_at")
                item_results.append(temp_data)

            if item_results:
                siemplify.result.add_data_table("Results", construct_csv(item_results))

        except Exception as e:
            siemplify.LOGGER.error("Failed to attach results JSON and/or table")
            siemplify.LOGGER.exception(e)

        result_value = True
        output_massage = f"Found {len(item_results)} results for search."

    else:
        output_massage = "No results were found."

    siemplify.end(output_massage, result_value)


if __name__ == "__main__":
    main()
