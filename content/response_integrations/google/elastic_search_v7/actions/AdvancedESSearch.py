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
from TIPCommon import dict_to_flat, construct_csv, extract_configuration_param
import json

INTEGRATION_NAME = "ElasticSearchV7"
SCRIPT_NAME = "ElasticSearchV7-AdvancedESSearch"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    # Integration Parameters
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=False,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )
    authenticate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Authenticate",
        is_mandatory=True,
        default_value=False,
        input_type=bool,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        default_value=False,
        input_type=bool,
    )
    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
        input_type=str,
    )

    if authenticate:
        elasticsearch_wrapper = ElasticsearchManager(
            server_address,
            username=username,
            password=password,
            api_token=api_token,
            verify_ssl=verify_ssl,
            authenticate=True,
            ca_certificate_file=ca_certificate_file,
        )
    else:
        elasticsearch_wrapper = ElasticsearchManager(
            server_address,
            verify_ssl=verify_ssl,
            ca_certificate_file=ca_certificate_file,
        )

    kwargs = {}

    kwargs["Index"] = siemplify.parameters.get("Index")
    kwargs["Query"] = siemplify.parameters.get("Query")
    kwargs["Display Field"] = siemplify.parameters.get("Display Field")
    kwargs["Search Field"] = siemplify.parameters.get("Search Field")
    kwargs["Timestamp Field"] = siemplify.parameters.get("Timestamp Field")
    kwargs["Oldest Date"] = siemplify.parameters.get("Oldest Date")
    kwargs["Earliest Date"] = siemplify.parameters.get("Earliest Date")
    kwargs["Limit"] = siemplify.parameters.get("Limit")
    kwargs["Oldest Date Compare Type"] = "gte"
    kwargs["Earliest Date Compare Type"] = "lte"

    results, status, total_hits = elasticsearch_wrapper.advanced_es_search(**kwargs)

    if status or results:
        output_message = (
            f"Query ran successfully {len(results)} hits found"
            if results
            else "No results found for the provided query."
        )
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
