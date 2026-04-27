from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CaSoapManager import CaSoapManager
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, construct_csv
import arrow

PROVIDER = "CaServiceDesk"
OPEN_STATUS = "Open"
SCRIPT_NAME = "CA_Search Tickets"
TICKETS_TABLE_HEADER = "Tickets"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration(PROVIDER)
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    ticket_fields_str = conf.get("Ticket Fields", "")

    ticket_fields = ticket_fields_str.split(",")

    ca_manager = CaSoapManager(api_root, username, password)

    result_value = ""
    errors = []
    incidets_data = []

    # Parameters.
    incident_id_param = siemplify.parameters.get("Incident ID", "")
    summary_search_text = siemplify.parameters.get("Summary", "")
    description_serch_text = siemplify.parameters.get("Description", "")
    status = siemplify.parameters.get("Status")
    days_backwards = int(siemplify.parameters.get("Days Backwards", 1))

    # Calculate unixtime to fetch from.
    time_to_fetch_unixtime = convert_datetime_to_unix_time(
        arrow.now().shift(days=-days_backwards).datetime
    )

    status_id = None

    if status:
        status_id = ca_manager.get_status_id_by_status(status)
    if incident_id_param:
        incident_ids = [incident_id_param]
    else:
        incident_ids = ca_manager.get_incident_ids_by_filter(
            summary_filter=summary_search_text,
            description_filter=description_serch_text,
            status_filter=status_id,
            last_modification_unixtime_milliseconds=time_to_fetch_unixtime,
        )
    if incident_ids:
        for incident_id in incident_ids:
            try:
                incidets_data.append(
                    ca_manager.get_incident_by_id(incident_id, ticket_fields)
                )
            except Exception as err:
                error_message = f"Filed fetching incident data for incident with ID: {incident_id}, ERROR: {str(err)}"
                siemplify.LOGGER.error(error_message)
                siemplify.LOGGER.exception(err)
                errors.append(error_message)

        if incidets_data:
            siemplify.result.add_data_table(
                TICKETS_TABLE_HEADER, construct_csv(incidets_data)
            )

        output_message = f"Found incidents with ids: {', '.join(incident_ids)}"
        result_value = incident_ids[-1]
    else:
        output_message = "No incidents were found."

    if errors:
        output_message = "{0} \n \n Errors: \n {1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.result.add_result_json(incidets_data)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
