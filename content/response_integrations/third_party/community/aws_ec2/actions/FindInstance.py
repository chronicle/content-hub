from __future__ import annotations

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EC2Manager import EC2Manager

IDENTIFIER = "AWS - EC2"
SCRIPT_NAME = "AWS EC2 - Find Instance"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
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
    instances_ids = siemplify.extract_action_param("Instance Ids")
    filters = siemplify.extract_action_param("Filters")
    max_results = siemplify.extract_action_param("Max Results", input_type=int)

    # Creating an instance of EC2Manager object
    ec2_manager = EC2Manager(access_key_id, secret_access_key, default_region)

    json_result = {}
    found_instances_ids = []
    not_found_instances_ids = []
    filters_list = []

    if filters is not None:
        filters = json.loads(filters)
        filters_list.append(filters)

    if filters is None:
        filters = [{}]

    if instances_ids is not None:
        instances_ids = instances_ids.split(",")
        for instance in instances_ids:
            instance = instance.strip()
            try:
                instance_details = ec2_manager.describe_instances(
                    instance,
                    filters_list,
                    max_results,
                )
                siemplify.LOGGER.info(
                    f"The instance {instance} was fetched successfully",
                )
                found_instances_ids.append(instance)
                json_result[instance] = instance_details

            except Exception as e:
                not_found_instances_ids.append(instance)
                siemplify.LOGGER.error(
                    f"Error occured when fetching the instance {instance}.\nError: {e}",
                )

    else:
        found_instances_details = ec2_manager.describe_instances(
            instances_ids,
            filters_list,
            max_results,
        )
        json_result = found_instances_details
        output_message = "All the instances were fetched successfully"
        result_value = True

    if len(found_instances_ids) > 0:
        output_message = (
            f"The instances {found_instances_ids} were fetched successfully.\n"
        )
        result_value = True

    if len(found_instances_ids) > 0 and len(not_found_instances_ids) > 0:
        output_message += f"The instances {not_found_instances_ids} were not fetched"

    siemplify.result.add_result_json(json_result)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
