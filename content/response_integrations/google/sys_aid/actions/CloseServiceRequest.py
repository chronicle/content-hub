from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SysAidManager import SysAidManager


PROVIDER = "SysAid"
ACTION_NAME = "SysAid - CloseServiceRequest"


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
    solution = siemplify.parameters.get("Solution")

    sysaid_manager.close_service_request(sr_id, solution)
    siemplify.end(
        f"Successfully closed service request {sr_id} with solution: {solution}.",
        "true",
    )


if __name__ == "__main__":
    main()
