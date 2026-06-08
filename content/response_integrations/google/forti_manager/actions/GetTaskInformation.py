# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
