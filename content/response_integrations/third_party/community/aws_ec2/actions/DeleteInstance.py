from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EC2Manager import EC2Manager

IDENTIFIER = "AWS - EC2"
SCRIPT_NAME = "AWS EC2 - Delete Instance"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    # Extracting the integration parameters
    access_key_id = siemplify.extract_configuration_param(IDENTIFIER, "Access Key ID")
    secret_access_key = siemplify.extract_configuration_param(
        IDENTIFIER,
        "Secret Access Key",
    )
    default_region = siemplify.extract_configuration_param(IDENTIFIER, "Default Region")

    # Extracting the action parameters
    instances_ids = siemplify.extract_action_param("Instance Ids")

    # Converting the instances_ids string into a list
    instances_ids_list = instances_ids.split(",")

    # Creating an instance of EC2Manager object
    ec2_manager = EC2Manager(access_key_id, secret_access_key, default_region)

    deleted_instances_details = []
    deleted_instances_ids = []
    not_deleted_instances_ids = []
    shutting_down_instances_ids = []
    json_result = {}

    status = EXECUTION_STATE_COMPLETED
    output_message = [""]
    result_value = 0

    for instance in instances_ids_list:
        instance = instance.strip()
        try:
            instance_details = ec2_manager.delete_instance(instance)
            current_state = (
                instance_details.get("TerminatingInstances")[0]
                .get("CurrentState")
                .get("Name")
            )

            if current_state == "shutting-down":
                siemplify.LOGGER.info(
                    f"The instance {instance} is in the process of shutting-down",
                )
                shutting_down_instances_ids.append(instance)

            if current_state == "terminated":
                siemplify.LOGGER.info(
                    f"The instance {instance} was deleted successfully",
                )
                deleted_instances_ids.append(instance)
                json_result[instance] = instance_details

            else:
                raise Exception(
                    f"The instance can not be deleted from the current state {current_state}, please try again.",
                )

        except Exception as e:
            not_deleted_instances_ids.append(instance)
            siemplify.LOGGER.error(
                f"Error occured when deleting the instance {instance}.\nError: {e}",
            )

    if len(shutting_down_instances_ids) > 0:
        status = EXECUTION_STATE_INPROGRESS
        output_message.append(
            f"The instances {shutting_down_instances_ids} are in the process of shutting down",
        )

    if len(deleted_instances_ids) > 0:
        output_message.append(
            f"The instances {deleted_instances_ids} were deleted successfully.",
        )
        result_value = True

    result_value = len(deleted_instances_ids)

    siemplify.result.add_result_json(json_result)
    print(json.dumps(json_result))
    siemplify.end("\n".join(output_message), result_value, status)


if __name__ == "__main__":
    main()
