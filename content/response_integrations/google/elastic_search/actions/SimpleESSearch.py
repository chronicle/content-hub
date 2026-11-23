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
from ..core.ElasticsearchManager import ElasticsearchManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import construct_csv, dict_to_flat
import json


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("ElasticSearch")
    server_address = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    ca_certificate_file = conf["CA Certificate File"]
    authenticate = conf["Authenticate"].lower() == "true"
    verify_ssl = conf["Verify SSL"].lower() == "true"

    if authenticate:
        elasticsearch_wrapper = ElasticsearchManager(
            server_address,
            username,
            password,
            verify_ssl=verify_ssl,
            ca_certificate_file=ca_certificate_file,
        )
    else:
        elasticsearch_wrapper = ElasticsearchManager(
            server_address,
            verify_ssl=verify_ssl,
            ca_certificate_file=ca_certificate_file,
        )

    index = siemplify.parameters.get("Index")
    query = siemplify.parameters.get("Query")
    limit = siemplify.parameters.get("Limit")

    results, status, total_hits = elasticsearch_wrapper.simple_es_search(
        index, query, limit
    )
    if status:
        output_message = f"Query ran successfully {len(results)} hits found"
    else:
        output_message = "ERROR: Query failed to run"

    if results:
        flat_results = []
        for result in results:
            flat_result = dict_to_flat(result)
            flat_results.append(flat_result)

        csv_output = construct_csv(flat_results)
        siemplify.result.add_data_table(f"Results - Total {len(results)}", csv_output)

    siemplify.result.add_result_json(json.dumps(results))
    siemplify.end(output_message, json.dumps(results))


if __name__ == "__main__":
    main()
