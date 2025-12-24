from __future__ import annotations

import json
import sys

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EC2Manager import EC2Manager

IDENTIFIER = "AWS - EC2"
SCRIPT_NAME = "AWS EC2 - Create Instance"


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    mode = "Main" if is_first_run else "InstanceState"

    output_message = [""]
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    json_result = {}

    # Extracting the integration parameters
    access_key_id = siemplify.extract_configuration_param(IDENTIFIER, "Access Key ID")
    secret_access_key = siemplify.extract_configuration_param(
        IDENTIFIER,
        "Secret Access Key",
    )
    default_region = siemplify.extract_configuration_param(IDENTIFIER, "Default Region")

    # Extracting the action parameters
    image_id = siemplify.extract_action_param("Image ID")
    instance_type = siemplify.extract_action_param("Instance Type")
    max_count = siemplify.extract_action_param("Max Count", input_type=int)
    min_count = siemplify.extract_action_param("Min Count", input_type=int)
    security_groups_id = siemplify.extract_action_param("Security Group ID")

    # Creating an instance of EC2Manager object
    ec2_manager = EC2Manager(access_key_id, secret_access_key, default_region)

    if is_first_run:
        pending_instances_ids = []
        try:
            instances_details = ec2_manager.create_instance(
                image_id,
                instance_type,
                max_count,
                min_count,
                security_groups_id,
            )
            for instance in instances_details["Instances"]:
                instance_id = instance.get("InstanceId")
                instance_state = instance.get("State").get("Name")

                if instance_state == "pending":
                    siemplify.LOGGER.info(f"The instance {instance_id} is pending.")
                    pending_instances_ids.append(instance_id)

                elif instance_state == "running":
                    siemplify.LOGGER.info(
                        f"The instance {instance_id} was created successfully",
                    )
                    json_result[instance_id] = instances_details

                else:
                    raise Exception(
                        f"Error occured when creating the instance for the Image {image_id}.",
                    )

            if len(pending_instances_ids) > 0:
                status = EXECUTION_STATE_INPROGRESS
                result_value = json.dumps(pending_instances_ids)
                output_message.append(
                    f"The following instances are pending:\n{pending_instances_ids}",
                )

        except Exception as e:
            siemplify.LOGGER.error(
                f"Error occured when creating the instance for the Image: {image_id}.\nError: {e}",
            )

    else:
        new_pending_instances_ids = []

        instances_to_check_the_state = json.loads(
            siemplify.parameters["additional_data"],
        )
        for instance in instances_to_check_the_state:
            instance_details = ec2_manager.describe_instances(instance)
            instance_id = (
                instance_details.get("Reservations")[0]
                .get("Instances")[0]
                .get("InstanceId")
            )
            current_instance_state = (
                instance_details.get("Reservations")[0]
                .get("Instances")[0]
                .get("State")
                .get("Name")
            )

            if current_instance_state == "pending":
                siemplify.LOGGER.info(f"The instance {instance_id} is still pending.")
                new_pending_instances_ids.append(instance_id)

            elif current_instance_state == "running":
                json_result[instance] = instance_details
                siemplify.LOGGER.info(
                    f"The instance {instance_id} was created successfully",
                )

            else:
                raise Exception(
                    f"Error occured when creating the instance for the image {image_id}.",
                )

        if len(new_pending_instances_ids) > 0:
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps(new_pending_instances_ids)
            output_message.append(
                f"The following instances are still pending:\n{new_pending_instances_ids}",
            )

        else:
            status = EXECUTION_STATE_COMPLETED
            result_value = True
            output_message.append(
                f"The instance of the Image {image_id} was created successfully.",
            )

    siemplify.result.add_result_json(json_result)
    siemplify.end("\n".join(output_message), result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
