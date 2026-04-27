from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeWebGatewayManager import McAfeeWebGatewayManager

# Consts
DEFAULT_DESCRIPTION = "Added by Siemplify"
SCRIPT_NAME = "McAfeeWebGateway - BlockIP"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("McAfeeWebGateway")

    server_address = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]

    mwb = McAfeeWebGatewayManager(server_address, username, password)

    group_name = siemplify.parameters["Group Name"]
    description = siemplify.parameters.get("Description") or DEFAULT_DESCRIPTION

    success_list = []
    failed_list = []
    output_message = ""
    result_value = "true"

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            try:
                res = mwb.insert_entry_to_list_by_name(
                    group_name, f"{entity.identifier}/32", description
                )
                if res:
                    success_list.append(entity.identifier)
                else:
                    failed_list.append(entity.identifier)
            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(f"Entity: {entity.identifier}. Error: {str(e)}.")
                siemplify.LOGGER._log.exception(e)

    if success_list:
        output_message += "Following IPs were successfully blocked:\n{}\n\n".format(
            "\n".join(success_list)
        )
    if failed_list:
        result_value = "false"
        output_message += "Failed to block following IPs\n{}\n\n".format(
            "\n".join(failed_list)
        )
    if not failed_list and not success_list:
        result_value = "false"
        output_message = "No changes made."

    mwb.logout()
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
