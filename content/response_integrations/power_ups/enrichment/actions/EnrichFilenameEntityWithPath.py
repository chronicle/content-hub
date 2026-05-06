# Copyright 2025 Google LLC
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

import ntpath
import os
import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler


def get_filename_from_path(path):
    is_win = re.match(r"^[A-Za-z]:\\", path.strip())
    if is_win:
        (file_path, full_file_name) = ntpath.split(path)
    else:
        file_path, full_file_name = os.path.split(path)
    _filename, file_extension = os.path.splitext(full_file_name)
    file_details = {}
    if file_path:
        file_details["file_name"] = full_file_name
        file_details["file_path"] = file_path
        file_details["file_extension"] = file_extension
        return file_details
    return None


@output_handler
def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = "output message :"  # human readable message, showed in UI as the action result
    result_value = None  # Set a simple result value, used for playbook if\else and placeholders.
    json_results = {}
    entities_to_update = []
    for entity in siemplify.target_entities:
        try:
            file_details = get_filename_from_path(entity.identifier)
            if file_details:
                json_results[entity.identifier] = file_details
                entity.additional_properties.update(file_details)
                entities_to_update.append(entity)
        except Exception:
            output_message += f"Entity {entity.identifier} was not able to be parsed.\n"
    if entities_to_update:
        siemplify.LOGGER.info("Updating entities")
        siemplify.update_entities(entities_to_update)
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

        output_message += f"The following entities were enriched: {','.join([entity.identifier for entity in siemplify.target_entities])}"

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
