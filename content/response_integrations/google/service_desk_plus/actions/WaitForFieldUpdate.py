from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from ..core.ServiceDeskPlusManager import ServiceDeskPlusManager
import sys


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "ServiceDesk Plus - Wait For Field Update"
    siemplify.LOGGER.info("=======Action START=======")

    request_id = siemplify.parameters["Request ID"]
    field = siemplify.parameters["Field Name"]

    output_message = f"Waiting for field {field} update."
    siemplify.end(output_message, request_id, EXECUTION_STATE_INPROGRESS)


def query_job():
    siemplify = SiemplifyAction()
    siemplify.script_name = "ServiceDesk Plus - Wait For Field Update"
    conf = siemplify.get_configuration("ServiceDeskPlus")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]

    service_desk_plus_manager = ServiceDeskPlusManager(api_root, api_key)

    # Parameters
    field = siemplify.parameters["Field Name"]
    values = siemplify.parameters["Values"]

    is_updated = False

    # Extract statues
    request_id = siemplify.parameters["additional_data"]

    if values:
        # Split string to list.
        values_list = values.lower().split(",")
    else:
        values_list = []

    # Get ticket status
    request = service_desk_plus_manager.get_request(request_id)
    value = request.get(field).lower()

    if value and value in values_list:
        # Incident state was updated
        is_updated = True

    if is_updated:
        siemplify.LOGGER.info(f"Request {request_id}, field {field} value: {value}")
        siemplify.LOGGER.info("=======Action DONE=======")
        output_message = f"Request {request_id}, field {field} value: {value}"
        siemplify.end(output_message, value, EXECUTION_STATE_COMPLETED)

    else:
        output_message = (
            f"Continuing...waiting for request {request_id} field {field} to be updated"
        )
        siemplify.LOGGER.info(
            f"Request {request_id} field {field} still not changed. Current value: {value}"
        )
        siemplify.end(output_message, request_id, EXECUTION_STATE_INPROGRESS)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        query_job()
