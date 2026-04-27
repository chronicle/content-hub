from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv
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

    request_info = service_desk_plus_manager.get_request(request_id)

    if request_info:
        # Add csv table
        flat_request = dict_to_flat(request_info)
        csv_output = flat_dict_to_csv(flat_request)
        siemplify.result.add_entity_table(f"Request {request_id}", csv_output)

        output_message = f"Request {request_id} was retrieved from ServiceDesk Plus."
        result_value = "true"

    else:
        output_message = f"Failed to retrieved ServiceDesk Plus request {request_id}."
        result_value = "false"

    siemplify.result.add_result_json(request_info or {})
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
