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

import json

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.rest.soar_api import save_attachment_to_case_wall

SCRIPT_NAME = "Add Attachment"


@output_handler
def main():
    siemplify = SiemplifyAction()

    description = siemplify.parameters.get("Description")
    name = siemplify.parameters.get("Name")
    file_type = siemplify.parameters.get("Type")
    base64_blob = siemplify.parameters.get("Base64 Blob")
    is_favorite = siemplify.parameters.get("isFavorite", "False").casefold() == "true"
    case_id = int(siemplify.case.identifier)
    attachment_data = CaseWallAttachment(
        name=name,
        file_type=file_type,
        base64_blob=base64_blob,
        is_important=is_favorite,
        case_id=case_id,
        description=description,
    )
    try:
        attachment = save_attachment_to_case_wall(
            chronicle_soar=siemplify,
            attachment_data=attachment_data
        )

    except requests.HTTPError as e:
        siemplify.LOGGER.error(f"Error occurred while adding attachment. Error: {e}")
        siemplify.LOGGER.exception(e)
        output_message = f'Error executing action "{SCRIPT_NAME}": {e}'
        siemplify.end(output_message, False, EXECUTION_STATE_FAILED)

    json_response = attachment.json()

    siemplify.result.add_result_json(json.dumps(json_response))

    output_message = "Successfully added attachment to the case."
    siemplify.end(output_message, True, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
