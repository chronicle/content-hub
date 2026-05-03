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
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SiemplifyUtilitiesManager import SiemplifyUtilitiesManager
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param

ACTION_NAME = "SiemplifyUtilities_Query Joiner"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    delimiter = siemplify.parameters.get("Delimiter", ",").strip() or ","

    values_str = siemplify.parameters.get("Values")
    query_values = values_str.split(delimiter) if values_str else []
    query_field = siemplify.parameters.get("Query Field")
    query_operator = siemplify.parameters.get("Query Operator")

    add_single_quotes = extract_action_param(
        siemplify,
        param_name="Add Quotes",
        default_value=False,
        input_type=bool,
        is_mandatory=False,
    )
    add_double_quotes = extract_action_param(
        siemplify,
        param_name="Add Double Quotes",
        default_value=False,
        input_type=bool,
        is_mandatory=False,
    )

    query = SiemplifyUtilitiesManager.form_query(
        query_field, query_operator, query_values, add_single_quotes, add_double_quotes
    )

    output_message = f"Successfully formed query: {query}"

    siemplify.end(output_message, query)


if __name__ == "__main__":
    main()
