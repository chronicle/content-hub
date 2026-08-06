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
from soar_sdk.SiemplifyUtils import construct_csv, dict_to_flat
from ..core.SysAidManager import SysAidManager
import json


PROVIDER = "SysAid"
ACTION_NAME = "SysAid - ListServiceRequests"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.action_definition_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)
    verify_ssl = conf.get("Verify SSL").lower() == "true"
    sysaid_manager = SysAidManager(
        server_address=conf.get("Api Root"),
        username=conf.get("Username"),
        password=conf.get("Password"),
        verify_ssl=verify_ssl,
    )

    sr_type = siemplify.parameters.get("Service Request Type")
    status = siemplify.parameters.get("Status")
    priority = siemplify.parameters.get("Priority")
    assignee = siemplify.parameters.get("Assignee")
    urgency = siemplify.parameters.get("Urgency")
    request_user = siemplify.parameters.get("Request User")
    assigned_group = siemplify.parameters.get("Assigned Group")
    category = siemplify.parameters.get("Category")
    sub_category = siemplify.parameters.get("Subcategory")
    third_category = siemplify.parameters.get("Third Category")
    get_archived = siemplify.parameters.get("Get Archived", "False").lower() == "true"

    service_requests = sysaid_manager.list_service_requests(
        sr_type=sr_type,
        get_archived=1 if get_archived else 0,
        status=status,
        priority=priority,
        assignee=assignee,
        urgency=urgency,
        request_user=request_user,
        category=category,
        sub_category=sub_category,
        third_category=third_category,
        assigned_group=assigned_group,
    )

    output_message = f"Found {len(service_requests)} service requests"

    if service_requests:
        flat_service_requests = list(map(dict_to_flat, service_requests))
        csv_output = construct_csv(flat_service_requests)
        siemplify.result.add_data_table("SysAid - Service Requests", csv_output)

    siemplify.end(output_message, json.dumps(service_requests))


if __name__ == "__main__":
    main()
