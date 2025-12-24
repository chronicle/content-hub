from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EC2Manager import EC2Manager

IDENTIFIER = "AWS - EC2"
SCRIPT_NAME = "AWS EC2 - Start Instance"
ec2_waiter_name = "instance_running"


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

    not_started_instances_ids = []
    pending_instances_ids = []
    started_instances_ids = []
    json_result = {}

    status = EXECUTION_STATE_COMPLETED
    result_value = 0
    output_message = [""]

    for instance in instances_ids_list:
        instance = instance.strip()
        try:
            instance_details = ec2_manager.start_instances(instance)
            current_state = (
                instance_details.get("StartingInstances")[0]
                .get("CurrentState")
                .get("Name")
            )
            if current_state == "pending":
                siemplify.LOGGER.info(f"The instance {instance} is pending")
                pending_instances_ids.append(instance)

            if current_state == "running":
                siemplify.LOGGER.info(
                    f"The instance {instance} was started successfully",
                )
                started_instances_ids.append(instance)
                json_result[instance] = instance_details

            else:
                raise Exception(
                    f"The instance cannot be started from the current state {current_state}, please try again.",
                )

        except Exception as e:
            not_started_instances_ids.append(instance)
            siemplify.LOGGER.error(
                f"Error occured when starting the instance {instance}.\nError: {e}",
            )

    if len(pending_instances_ids) > 0:
        output_message.append(f"The instances {pending_instances_ids} are pending.")
        status = EXECUTION_STATE_INPROGRESS

    if len(started_instances_ids) > 0:
        output_message.append(
            f"The instances {started_instances_ids} were started successfully.",
        )

        # The result value is the count of started instances.
        result_value = len(started_instances_ids)

    siemplify.result.add_result_json(json_result)
    siemplify.end("\n".join(output_message), result_value, status)


if __name__ == "__main__":
    main()
