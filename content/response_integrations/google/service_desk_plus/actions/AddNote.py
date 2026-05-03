from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
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
    note = siemplify.parameters["Note"]
    is_public = siemplify.parameters.get("Is Public", "false").lower() == "true"

    service_desk_plus_manager.add_note(request_id, is_public, note)

    output_message = f"Successfully added note to request {request_id}."
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
