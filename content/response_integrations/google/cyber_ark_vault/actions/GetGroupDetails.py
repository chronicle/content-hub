from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CyberarkVaultManager import CyberarkManager
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("CyberArkVault")
    username = conf["Username"]
    password = conf["Password"]
    use_ssl = conf["Use SSL"]
    api_root = conf["Api Root"]

    cyberark_manager = CyberarkManager(username, password, api_root, use_ssl)

    group_name = siemplify.parameters["Group Name"]

    group_details = cyberark_manager.get_group_details(group_name)
    if group_details:
        flat_report = dict_to_flat(group_details)
        siemplify.result.add_data_table(
            f"{group_name} Details:", flat_dict_to_csv(flat_report)
        )
        output_message = "Attached group details."
        result_value = "true"
    else:
        output_message = "Group not found."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
