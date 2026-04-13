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
from ..core.ShodanManager import ShodanManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import flat_dict_to_csv, dict_to_flat
import json


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("Shodan")
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"
    api_key = conf.get("API key", "")
    shodan = ShodanManager(api_key, verify_ssl=verify_ssl)

    # Parameters:
    query = siemplify.parameters["Search Query"]
    minify = siemplify.parameters.get("Set Minify", "False").lower() == "true"
    facets = siemplify.parameters.get("Facets", "")

    search_res = shodan.search(query, facets=facets, minify=minify)
    json_results = {}
    if search_res:
        json_results = search_res
        # Add csv table
        flat_report = dict_to_flat(search_res)
        siemplify.result.add_data_table("Search Results:", flat_dict_to_csv(flat_report))
        output_message = "Successfully search the SHODAN database"
        result_value = json.dumps(search_res)
    else:
        output_message = "Failed to search the SHODAN database"
        result_value = "{}"

    # add json
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
