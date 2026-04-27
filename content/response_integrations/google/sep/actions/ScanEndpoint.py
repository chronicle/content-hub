from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SEPManager import SEP14Manager, VALID_SCAN_TYPES
from TIPCommon import extract_configuration_param


INTEGRATION_NAME = "SEP"
ACTION_NAME = "SEP - Scan"
COMMAND = "sep_scan_command_id"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    output_message = ""
    errors = ""

    siemplify.LOGGER.info("Starting Action")

    conf = siemplify.get_configuration("SEP")
    username = conf["Username"]
    password = conf["Password"]
    domain = conf["Domain"]
    url = conf["Api Root"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )
    sep_manager = SEP14Manager(url, username, password, domain, verify_ssl=verify_ssl)

    scan_type = siemplify.parameters.get("Scan Type", "ScanNow_Full")

    if scan_type not in VALID_SCAN_TYPES:
        siemplify.end(f"Scan type {scan_type} is not valid.", "false")

    siemplify.LOGGER.info("Connected.")

    enriched_entities = []
    commands_ids = []

    for entity in siemplify.target_entities:
        try:
            computer_id = None

            if entity.entity_type == EntityTypes.ADDRESS:
                computer_id = sep_manager.getComputerIdByIP(entity.identifier)

            elif entity.entity_type == EntityTypes.HOSTNAME:
                computer_info = sep_manager.getComputerInfo(entity.identifier)
                if computer_info:
                    computer_id = sep_manager.getComputerIdByComputerName(
                        computer_info["computerName"]
                    )

            if computer_id:
                siemplify.LOGGER.info(f"Scanning {entity.identifier}")

                command_id = sep_manager.runScan(computer_id, scan_type)

                entity.additional_properties.update({COMMAND: command_id})

                enriched_entities.append(entity)
                commands_ids.append(command_id)

        except Exception as e:
            errors += f"Scan failed on {entity.identifier}:\n{e}\n"
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.exception(e)
            continue

    if enriched_entities:
        entities_names = [
            f"{entity.identifier}: {entity.additional_properties[ COMMAND]}\n"
            for entity in enriched_entities
        ]

        output_message += (
            "Scanning the following entities:\n"
            + "\n".join(entities_names)
            + "\n Command Ids:\n"
            + "\n".join(commands_ids)
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)
        siemplify.end(output_message, ",".join(commands_ids))

    else:
        output_message += "No suitable entities were found.\n"
        output_message += errors

        siemplify.end(output_message, ",".join(commands_ids))


if __name__ == "__main__":
    main()
