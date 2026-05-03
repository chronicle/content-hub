from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import *
from ..core.FortiManager import FortiManager
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv


PROVIDER = "FortiManager"
ACTION_NAME = "FortiManager_Get Task Information"
TABLE_HEADER = "Task Information"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    forti_manager = FortiManager(
        conf["API Root"], conf["Username"], conf["Password"], verify_ssl
    )

    result_value = False

    # Parameters.
    task_id = siemplify.parameters.get("Task ID")

    task_object = forti_manager.get_task(task_id)

    if task_object:
        siemplify.result.add_data_table(
            TABLE_HEADER, flat_dict_to_csv(dict_to_flat(task_object))
        )
        output_message = f"Found information for task with ID: {task_id}"
        result_value = True
    else:
        output_message = f"No information found for task with ID: {task_id}"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
