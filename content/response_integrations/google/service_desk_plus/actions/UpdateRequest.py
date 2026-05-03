from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ServiceDeskPlusManager import ServiceDeskPlusManager, DUE_DATE_FORMAT


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("ServiceDeskPlus")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]

    service_desk_plus_manager = ServiceDeskPlusManager(api_root, api_key)

    # Parameters
    request_id = siemplify.parameters.get("Request ID")
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

    service_desk_plus_manager.update_request(
        request_id=request_id,
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

    output_message = (
        f"ServiceDesk Plus request - {request_id} was updated successfully."
    )
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
