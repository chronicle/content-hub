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
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv
from ..core.ServiceDeskPlusManager import ServiceDeskPlusManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("ServiceDeskPlus")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]

    service_desk_plus_manager = ServiceDeskPlusManager(api_root, api_key)

    # Parameters
    request_id = siemplify.parameters["Request ID"]

    request_info = service_desk_plus_manager.get_request(request_id)

    if request_info:
        # Add csv table
        flat_request = dict_to_flat(request_info)
        csv_output = flat_dict_to_csv(flat_request)
        siemplify.result.add_entity_table(f"Request {request_id}", csv_output)

        output_message = f"Request {request_id} was retrieved from ServiceDesk Plus."
        result_value = "true"

    else:
        output_message = f"Failed to retrieved ServiceDesk Plus request {request_id}."
        result_value = "false"

    siemplify.result.add_result_json(request_info or {})
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
