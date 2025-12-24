from __future__ import annotations

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EC2Manager import EC2Manager

IDENTIFIER = "AWS - EC2"
SCRIPT_NAME = "AWS EC2 - Authorize Security Group Ingress"


@output_handler
def main():
    siemplify = SiemplifyAction()
    authorized_security_group = {}
    output_message = ""
    result_value = False

    # Extracting the integration parameters
    access_key_id = siemplify.extract_configuration_param(IDENTIFIER, "Access Key ID")
    secret_access_key = siemplify.extract_configuration_param(
        IDENTIFIER,
        "Secret Access Key",
    )
    default_region = siemplify.extract_configuration_param(IDENTIFIER, "Default Region")

    # Extracting the action parameters
    group_id = siemplify.extract_action_param("Group ID")
    ip_permisssions = siemplify.extract_action_param("IP Permissions")

    ip_permisssions_dict = [json.loads(ip_permisssions)]

    # Creating an instance of EC2Manager object
    ec2_manager = EC2Manager(access_key_id, secret_access_key, default_region)

    try:
        authorized_security_group = ec2_manager.authorize_security_group_ingress(
            group_id,
            ip_permisssions_dict,
        )
        siemplify.LOGGER.info(
            f"The secrurity group id {group_id} was authorized successfully",
        )
        siemplify.result.add_result_json(authorized_security_group)

    except Exception as e:
        siemplify.LOGGER.error(
            f"Error occured when authorizing the secrurity group id {group_id}.\nError: {e}",
        )

    if authorized_security_group:
        output_message = (
            f"The secrurity group id {group_id} was authorized successfully"
        )
        result_value = True

    else:
        output_message = "An error occured, checks the logs"
        result = False

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
