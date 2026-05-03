from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeWebGatewayManager import McAfeeWebGatewayManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("McAfeeWebGateway")

    server_address = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]

    result_value = "false"
    group_name = siemplify.parameters["Group Name"]
    item_to_delete = siemplify.parameters["Item To Delete"]

    mwb = McAfeeWebGatewayManager(server_address, username, password)

    res = mwb.delete_entry_from_list_by_name(group_name, item_to_delete)

    if res:
        result_value = "true"
        output_message = (
            f"Item {item_to_delete} was deleted successfully from {group_name}"
        )
    else:
        output_message = f"Failed to delete {item_to_delete} item from {group_name}. No changes made."

    mwb.logout()
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
