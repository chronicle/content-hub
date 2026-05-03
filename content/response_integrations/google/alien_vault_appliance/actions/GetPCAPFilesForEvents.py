from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.AlienVaultManager import AlienVaultManager
import base64

PROVIDER = "AlienVaultAppliance"
TABLE_NAME = "PCAP Records"
PCAP_FILE_NAME = "{0}_{1}.pcap"
ACTION_NAME = "CBResponse_Get PCAP For Events"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    configurations = siemplify.get_configuration(PROVIDER)
    server_address = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]

    alienvault_manager = AlienVaultManager(server_address, username, password)

    result_value = False
    errors = []
    json_result = {}

    for event in siemplify.current_alert.security_events:
        try:
            event_id = event.additional_properties.get("Id")
            if event_id:
                pcap_content = alienvault_manager.get_event_pcap(event_id)
                if pcap_content:
                    json_result[event_id] = base64.b64encode(pcap_content.encode())
                    siemplify.result.add_attachment(
                        event.name,
                        PCAP_FILE_NAME.format(event.name, event_id),
                        base64.b64encode(pcap_content.encode()),
                    )
                    result_value = True
            else:
                siemplify.LOGGER.info(f'Event "{event.name}" has no ID field')
        except Exception as err:
            error_message = f"Error fetching PCAP file for event {event.name}_{event_id}, ERROR: {str(err)}"
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(errors)

    if result_value:
        output_message = "Found PCAP files for events."
    else:
        output_message = "Not found PCAP files for events."

    if errors:
        output_message = "{0} \n \n Errors: \n \n  {1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.result.add_result_json(json_result)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
