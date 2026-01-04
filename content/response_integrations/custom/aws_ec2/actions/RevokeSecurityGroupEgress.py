from __future__ import annotations

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EC2Manager import EC2Manager

IDENTIFIER = "AWS - EC2"
SCRIPT_NAME = "AWS EC2 - Revoke Security Group Egress"


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = ""
    result_value = False
    revoked_security_group = {}

    # Extracting the integration parameterssg-1a2b3c4d
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
        revoked_security_group = ec2_manager.revoke_security_group_egress(
            group_id,
            ip_permisssions_dict,
        )
        siemplify.LOGGER.info(
            f"The outbound ip permissions of the security group id {group_id} were revoked successfully",
        )
        siemplify.result.add_result_json(revoked_security_group)
        print(json.dumps(revoked_security_group))

    except Exception as e:
        siemplify.LOGGER.error(
            f"Error occured when revoking the outbound ip permissions of the secrurity group id {group_id}.\nError: {e}",
        )

    if revoked_security_group:
        output_message = f"The outbound ip permissions of the security group id {group_id} were revoked successfully"
        result_value = True

    else:
        output_message = "An error occured, checks the logs"
        result = False

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
