from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeTIEDXLManager import McAfeeTIEDXLManager

SCRIPT_NAME = "Mcafee TIE & DXL - GetFileReferences"


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("McAfeeTIEDXL")
    siemplify.script_name = SCRIPT_NAME
    server_addr = conf["Server Address"]
    broker_ca_bundle_path = conf["Broker CA Bundle Path"]
    cert_file_path = conf["Client Cert File Path"]
    private_key_path = conf["Client Key File Path"]

    mcafee_dxl_manager = McAfeeTIEDXLManager(
        server_addr, broker_ca_bundle_path, cert_file_path, private_key_path
    )

    enriched_entities = []

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH:
            try:
                references = mcafee_dxl_manager.get_file_references(entity.identifier)

                if references:
                    # Attach references as csv
                    csv_output = mcafee_dxl_manager.construct_csv(references)
                    siemplify.result.add_entity_table(
                        f"References - {entity.identifier}", csv_output
                    )

                    enriched_entities.append(entity)

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER._log.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = (
            "McAfee TIE: References were found for the following entities:\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "McAfee TIE: No references were found."

    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
