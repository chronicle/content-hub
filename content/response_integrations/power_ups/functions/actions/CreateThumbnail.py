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

import base64
import io
import json

from PIL import Image
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

MISSING_VAL = "NotFound"


def find_key_path_in_json(key_path, json_data):
    """Finds the relevant key_path in a json object.
    If list encountered, if its of len 1, its value is used. Otherwise, it exits with default value (MULTIPLE VALUES FOUND)
    """
    return find_key_path_recursive(key_path, json_data)


def find_key_path_recursive(key_list, current_json):
    if key_list:
        if isinstance(current_json, list):
            if key_list:
                if len(current_json) == 1:
                    return find_key_path_recursive(key_list, current_json[0])
                return MULTIPLE_VALUES
            return ", ".join(current_json)
        if isinstance(current_json, dict):
            if key_list[0] in current_json:
                return find_key_path_recursive(key_list[1:], current_json[key_list[0]])
            # raise Exception("Key: {}, json: {}".format(key_list, current_json))
            return MISSING_VAL
    else:
        if isinstance(current_json, dict):
            raise Exception(
                f"Not a simple value.  Unable to enrich. Key: {key_list}, json: {current_json}",
            )
        if isinstance(current_json, list):
            return ",".join(current_json)

        return f"{current_json}"  # Found val, return it. Format to make everything into string


def create_thumbnail(base64_str, thumb_size):
    buffer = io.BytesIO()

    imgdata = base64.b64decode(base64_str)
    img = Image.open(io.BytesIO(imgdata))
    new_img = img.resize((int(thumb_size[0]), int(thumb_size[1])))  # x, y
    new_img.save(buffer, format="PNG")
    img_b64 = base64.b64encode(buffer.getvalue())
    return str(img_b64)[2:-1]


@output_handler
def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = (
        "output message :"  # human readable message, showed in UI as the action result
    )
    result_value = (
        None  # Set a simple result value, used for playbook if\else and placeholders.
    )

    base64_str = siemplify.extract_action_param("Base64 Image", print_value=False)
    thumb_size = list(
        filter(
            None,
            [x.strip() for x in siemplify.parameters.get("Thumbnail Size").split(",")],
        ),
    )
    input_json = siemplify.extract_action_param("Input JSON", print_value=False)
    image_key_path = list(
        filter(
            None,
            [x.strip() for x in siemplify.parameters.get("Image Key Path").split(".")],
        ),
    )

    json_result = {}

    if input_json is not None:
        in_json = json.loads(input_json)
        for entity_json in in_json:
            base64_str = find_key_path_in_json(image_key_path, entity_json)
            data = {}
            data["thumbnail"] = create_thumbnail(base64_str, thumb_size)
            json_result[entity_json["Entity"]] = data
            json_result = convert_dict_to_json_result_dict(json_result)
    else:
        data = {}
        data["thumbnail"] = create_thumbnail(base64_str, thumb_size)
        json_result = data

    siemplify.result.add_result_json(json_result)
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
