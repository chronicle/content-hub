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
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
import json

INTEGRATION_NAME = "ElasticSearchV7"
SCRIPT_NAME = "DSL Search"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"

    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=False,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=False,
        input_type=str,
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
        default_value=False,
        input_type=bool,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
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

    index = extract_action_param(
        siemplify,
        param_name="Index",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    query = extract_action_param(
        siemplify,
        param_name="Query",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )
    status = EXECUTION_STATE_COMPLETED

    try:
        if authenticate:
            elasticsearch_wrapper = ElasticsearchManager(
                server_address,
                username=username,
                password=password,
                api_token=api_token,
                verify_ssl=verify_ssl,
                authenticate=True,
                ca_certificate_file=ca_certificate_file,
                siemplify=siemplify,
            )
        else:
            elasticsearch_wrapper = ElasticsearchManager(
                server_address,
                verify_ssl=verify_ssl,
                ca_certificate_file=ca_certificate_file,
                siemplify=siemplify,
            )
        dsl_search_results, total_hits = elasticsearch_wrapper.dsl_search(
            index, query, limit
        )
        if dsl_search_results:
            output_message = f"Successfully executed ElasticSearch DSL Query {len(dsl_search_results)} hits found"
        else:
            output_message = "Error executing ElasticSearch action 'Run DSL Query'."

        if dsl_search_results:
            flat_results = []
            for dsl_result in dsl_search_results:
                flat_result = dsl_result.to_flat()
                flat_results.append(flat_result)

            csv_output = construct_csv(flat_results)
            siemplify.result.add_data_table(
                f"Results - Total {len(dsl_search_results)}", csv_output
            )

        siemplify.result.add_result_json(
            json.dumps([dsl_result.to_json() for dsl_result in dsl_search_results])
        )
        result = "true"

    except Exception as e:
        output_message = f"Failed to run DSL query. Error {e}"
        result = "false"
        status = EXECUTION_STATE_FAILED

        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
