from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from ..core.ServiceDeskPlusManager import ServiceDeskPlusManager
import sys


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "ServiceDesk Plus - Wait For Status Update"
    siemplify.LOGGER.info("=======Action START=======")

    request_id = siemplify.parameters["Request ID"]

    output_message = "Waiting for status update."
    siemplify.end(output_message, request_id, EXECUTION_STATE_INPROGRESS)


def query_job():
    siemplify = SiemplifyAction()
    siemplify.script_name = "ServiceDesk Plus - Wait For Status Update"
    conf = siemplify.get_configuration("ServiceDeskPlus")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]

    service_desk_plus_manager = ServiceDeskPlusManager(api_root, api_key)

    # Parameters
    statuses = siemplify.parameters["Statuses"]

    is_updated = False

    # Extract statues
    request_id = siemplify.parameters["additional_data"]

    if statuses:
        # Split string to list.
        statuses_list = statuses.lower().split(",")
    else:
        statuses_list = []

    # Get ticket status
    request = service_desk_plus_manager.get_request(request_id)
    status = request.get("status").lower()

    if status and status in statuses_list:
        # Incident state was updated
        is_updated = True

    if is_updated:
        siemplify.LOGGER.info(f"Request {request_id} Status: {status}")
        siemplify.LOGGER.info("=======Action DONE=======")
        output_message = f"Request {request_id} Status: {status}"
        siemplify.end(output_message, status, EXECUTION_STATE_COMPLETED)
    else:
        output_message = (
            f"Continuing...waiting for request {request_id} status to be updated"
        )
        siemplify.LOGGER.info(
            f"Request {request_id} status still not changed. Current status: {status}"
        )
        siemplify.end(output_message, request_id, EXECUTION_STATE_INPROGRESS)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        query_job()
