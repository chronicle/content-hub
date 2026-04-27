from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SysAidManager import SysAidManager

PROVIDER = "SysAid"
ACTION_NAME = "SysAid - CreateServiceRequest"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.action_definition_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)
    verify_ssl = conf.get("Verify SSL").lower() == "true"
    manager = SysAidManager(
        server_address=conf.get("Api Root"),
        username=conf.get("Username"),
        password=conf.get("Password"),
        verify_ssl=verify_ssl,
    )

    title = siemplify.parameters.get("Title")
    description = siemplify.parameters.get("Description")
    status = siemplify.parameters.get("Status")
    priority = siemplify.parameters.get("Priority")
    assignee = siemplify.parameters.get("Assignee")
    urgency = siemplify.parameters.get("Urgency")
    request_user = siemplify.parameters.get("Request User")
    assigned_group = siemplify.parameters.get("Assigned Group")
    category = siemplify.parameters.get("Category")
    sub_category = siemplify.parameters.get("Subcategory")
    third_category = siemplify.parameters.get("Third Category")

    service_request_id = manager.create_service_request(
        title=title,
        description=description,
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
    siemplify.end(
        f"Successfully created service request {service_request_id}.",
        service_request_id,
    )


if __name__ == "__main__":
    main()
