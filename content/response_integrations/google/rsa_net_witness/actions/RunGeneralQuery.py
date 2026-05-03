from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAManager import RSA
from soar_sdk.SiemplifyUtils import construct_csv
import base64
import json

# Consts.
RSA_PROVIDER = "RSANetWitness"
ACTION_NAME = "Update the 'TI' database of NetWitness"
TITLE = "Result PCAP"
FILE_NAME = "result_pcap.pcap"
TABLE_NAME = "Result Events"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    # Configuration.
    config = siemplify.get_configuration(RSA_PROVIDER)

    concentrator_uri = config["Concentrator Api Root"]
    decoder_uri = config["Decoder Api Root"]
    username = config["Username"]
    password = config["Password"]
    verify_ssl = config.get("Verify SSL", "false").lower() == "true"

    rsa_manager = RSA(
        concentrator_uri=concentrator_uri,
        decoder_uri=decoder_uri,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
    )

    # Variables Definition.
    result_value = ""
    events = []

    # Parameters.
    query = siemplify.parameters.get("Query")

    session_ids = rsa_manager.get_session_ids_for_query(query)

    if session_ids:
        # Get PCAP file.
        pcap_content = rsa_manager.get_pcap_of_session_id(",".join(session_ids))
        siemplify.result.add_attachment(
            TITLE, FILE_NAME, base64.b64encode(pcap_content)
        )
        # Get Events.
        for session_id in session_ids:
            try:
                events.append(rsa_manager.get_metadata_from_session_id(session_id))
            except Exception as err:
                error_massage = (
                    f"Error retrieving event for session ID: {session_id}, ERROR: {err}"
                )
                siemplify.LOGGER.error(error_massage)
                siemplify.LOGGER.exception(err)

        if events:
            siemplify.result.add_data_table(TABLE_NAME, construct_csv(events))
            result_value = json.dumps(events)

    if result_value:
        output_message = f'Found results for query - "{query}"'
    else:
        output_message = f'No results found for query - "{query}"'

    siemplify.result.add_result_json(events)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
