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
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
from soar_sdk.SiemplifyAction import SiemplifyAction
from service_desk_plus.core.ServiceDeskPlusManager import ServiceDeskPlusManager, DUE_DATE_FORMAT


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("ServiceDeskPlus")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]

    service_desk_plus_manager = ServiceDeskPlusManager(api_root, api_key)

    # Parameters
    subject = siemplify.parameters.get("Subject")
    requester = siemplify.parameters.get("Requester")
    description = siemplify.parameters.get("Description")
    status = siemplify.parameters.get("Status")
    technician = siemplify.parameters.get("Technician")
    priority = siemplify.parameters.get("Priority")
    urgency = siemplify.parameters.get("Urgency")
    category = siemplify.parameters.get("Category")
    request_template = siemplify.parameters.get("Request Template")
    request_type = siemplify.parameters.get("Request Type")
    due_by_time = (
        int(siemplify.parameters.get("Due By Time (ms)"))
        if siemplify.parameters.get("Due By Time (ms)")
        else None
    )
    mode = siemplify.parameters.get("Mode")
    level = siemplify.parameters.get("Level")
    site = siemplify.parameters.get("Site")
    group = siemplify.parameters.get("Group")
    impact = siemplify.parameters.get("Impact")

    request_id = service_desk_plus_manager.add_request(
        subject=subject,
        requester=requester,
        description=description,
        status=status,
        technician=technician,
        priority=priority,
        urgency=urgency,
        category=category,
        request_template=request_template,
        request_type=request_type,
        due_by_time=(
            convert_unixtime_to_datetime(due_by_time).strftime(DUE_DATE_FORMAT)
            if due_by_time
            else None
        ),
        mode=mode,
        level=level,
        site=site,
        group=group,
        impact=impact,
    )

    request = service_desk_plus_manager.get_request(request_id)
    siemplify.result.add_result_json(request)

    output_message = f"ServiceDesk Plus request - {request_id} was created."
    siemplify.end(output_message, str(request_id))


if __name__ == "__main__":
    main()
