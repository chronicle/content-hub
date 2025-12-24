from __future__ import annotations

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EC2Manager import EC2Manager

IDENTIFIER = "AWS - EC2"
SCRIPT_NAME = "AWS EC2 - Start Instance"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    output_message = ""
    result_value = False
    tags_to_create_list = []
    # Extracting the integration parameters
    access_key_id = siemplify.extract_configuration_param(IDENTIFIER, "Access Key ID")
    secret_access_key = siemplify.extract_configuration_param(
        IDENTIFIER,
        "Secret Access Key",
    )
    default_region = siemplify.extract_configuration_param(IDENTIFIER, "Default Region")

    # Extracting the action parameters
    resources_id = siemplify.extract_action_param("Resources ID")
    tags_to_create = siemplify.extract_action_param("Tags")

    # Creating an instance of EC2Manager object
    ec2_manager = EC2Manager(access_key_id, secret_access_key, default_region)

    # Converting the tags_to_create string into a list
    tags_to_create = json.loads(tags_to_create)
    tags_to_create_list = tags_to_create.get("tags")

    resources_id_list = resources_id.split(",")

    # Creating an instance of EC2Manager object
    ec2_manager = EC2Manager(access_key_id, secret_access_key, default_region)

    tagged_resources_details = []
    tagged_resources_ids = []
    not_tagged_resources_ids = []

    for resource in resources_id_list:
        resource = resource.strip()
        try:
            tagged_resource = ec2_manager.create_tags(resource, tags_to_create_list)
            siemplify.LOGGER.info(
                f"The tags were assigned to the resource:{resource} successfully.",
            )
            tagged_resources_ids.append(resource)
            tagged_resources_details.append(tagged_resource)
            siemplify.result.add_entity_json(
                f"The tags were assigned to the resource {resource}:",
                tagged_resources_details,
            )

        except Exception as e:
            not_tagged_resources_ids.append(resource)
            siemplify.LOGGER.error(
                f"Error occured when tagging the resource {resource}.\nError: {e}",
            )

    siemplify.result.add_result_json(tagged_resources_details)

    if len(tagged_resources_ids) > 0:
        output_message = f"The tags were assigned to the resources:{tagged_resources_ids} successfully.\n"
        result_value = True

    if len(not_tagged_resources_ids) > 0 and len(tagged_resources_ids) > 0:
        output_message += (
            f"The tags were not assigned to the resources: {not_tagged_resources_ids}."
        )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
