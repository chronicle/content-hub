from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EC2Manager import EC2Manager

IDENTIFIER = "AWS - EC2"
SCRIPT_NAME = "AWS EC2 - Stop Instance"


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
    force_instance_to_stop = siemplify.extract_action_param(
        "Force Instance To Stop",
        input_type=bool,
    )

    # Converting the instances_ids string into a list
    instances_ids_list = instances_ids.split(",")

    # Creating an instance of EC2Manager object
    ec2_manager = EC2Manager(access_key_id, secret_access_key, default_region)

    stopped_instances_ids = []
    not_stopped_instances_ids = []
    stopping_instances_ids = []
    json_result = {}

    status = EXECUTION_STATE_COMPLETED
    result_value = 0
    output_message = [""]

    for instance in instances_ids_list:
        instance = instance.strip()
        try:
            instance_details = ec2_manager.stop_instances(
                instance,
                force_instance_to_stop,
            )
            current_state = (
                instance_details.get("StoppingInstances")[0]
                .get("CurrentState")
                .get("Name")
            )

            if current_state == "stopping":
                siemplify.LOGGER.info(
                    f"The instance {instance} is in the process of stopping",
                )
                stopping_instances_ids.append(instance)

            if current_state == "stopped":
                siemplify.LOGGER.info(
                    f"The instance {instance} was stopped successfully",
                )
                json_result[instance] = instance_details
                stopped_instances_ids.append(instance)

            else:
                raise Exception(
                    f"The instance cannot be stopped from the current state {current_state} please try again",
                )

        except Exception as e:
            not_stopped_instances_ids.append(instance)
            siemplify.LOGGER.error(
                f"Error occured when stopping the instance {instance}.\nError: {e}",
            )

    if len(stopping_instances_ids) > 0:
        status = EXECUTION_STATE_INPROGRESS
        output_message.append(
            f"The instances {stopping_instances_ids} are in the process of stopping.",
        )

    if len(stopped_instances_ids) > 0:
        output_message.append(
            f"The instances {stopped_instances_ids} were stopped successfully.",
        )

    result_value = len(stopped_instances_ids)

    siemplify.result.add_result_json(json_result)
    siemplify.end("\n".join(output_message), result_value, status)


if __name__ == "__main__":
    main()
