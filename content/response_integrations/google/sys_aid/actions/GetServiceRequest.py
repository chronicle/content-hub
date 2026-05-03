from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SysAidManager import SysAidManager
import json


PROVIDER = "SysAid"
ACTION_NAME = "SysAid - GetServiceRequest"


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

    sr_id = siemplify.parameters.get("Service Request ID")

    service_request = sysaid_manager.get_service_request(sr_id)
    siemplify.result.add_json(
        f"SysAid - Service Request {sr_id}", json.dumps(service_request)
    )
    siemplify.end(
        f"Successfully fetched service request {sr_id}.", json.dumps(service_request)
    )


if __name__ == "__main__":
    main()
