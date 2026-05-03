from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ServiceDeskPlusManager import ServiceDeskPlusManager, DUE_DATE_FORMAT

TAG = "ServiceDeskPlus"


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("ServiceDeskPlus")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]

    context_alert_id = siemplify.current_alert.external_id
    service_desk_plus_manager = ServiceDeskPlusManager(api_root, api_key)

    # Parameters
    subject = siemplify.parameters.get("Subject")
    requester = siemplify.parameters.get("Requester")
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
        description=context_alert_id,
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

    # Add tag
    siemplify.add_tag(TAG)

    output_message = f"ServiceDesk Plus request - {request_id} was created."
    result_value = request_id
    # Attach request id to alert.
    siemplify.update_alerts_additional_data(
        {siemplify.current_alert.identifier: request_id}
    )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
