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

import dataclasses
import json

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.rest.soar_api import save_attachment_to_case_wall
from TIPCommon.types import SingleJson

SCRIPT_NAME = "Add Attachment"


@dataclasses.dataclass(slots=True)
class AttachmentResult:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        attachment_data = self.raw_data.pop("caseAttachment", {})
        evidence_name = attachment_data.pop("fileName", self.raw_data.pop("evidenceName", None))
        description = self.raw_data.pop("comment", self.raw_data.pop("description", None))
        evidence_thumbnail_base64 = self.raw_data.pop("evidenceThumbnailBase64", None)
        evidence_id = attachment_data.pop("attachmentId", self.raw_data.pop("evidenceId", 0))
        file_type = attachment_data.pop("fileType", self.raw_data.pop("fileType", None))
        creator_user_id = self.raw_data.pop("user", self.raw_data.pop("creatorUserId", None))
        id_ = self.raw_data.pop("id", None)
        case_id = self.raw_data.pop("case", self.raw_data.pop("caseId", -1))
        is_favorite = self.raw_data.pop("isFavorite", False)
        update_time = self.raw_data.pop(
            "updateTime", self.raw_data.pop("modificationTimeUnixTimeInMs", -1)
        )
        create_time = self.raw_data.pop(
            "createTime", self.raw_data.pop("creationTimeUnixTimeInMs", -1)
        )
        alert_identifier = self.raw_data.pop("alertIdentifier", None)
        return {
            "evidenceName": evidence_name,
            "description": description,
            "evidenceThumbnailBase64": evidence_thumbnail_base64,
            "evidenceId": evidence_id,
            "fileType": file_type,
            "creatorUserId": creator_user_id,
            "id": id_,
            "type": 4,
            "caseId": case_id,
            "isFavorite": is_favorite,
            "modificationTimeUnixTimeInMs": update_time,
            "creationTimeUnixTimeInMs": create_time,
            "alertIdentifier": alert_identifier,
            **self.raw_data,
            **attachment_data,
        }


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
        attachment = AttachmentResult(
            save_attachment_to_case_wall(chronicle_soar=siemplify, attachment_data=attachment_data)
        )

    except requests.HTTPError as e:
        siemplify.LOGGER.error(f"Error occurred while adding attachment. Error: {e}")
        siemplify.LOGGER.exception(e)
        output_message = f'Error executing action "{SCRIPT_NAME}": {e}'
        siemplify.end(output_message, False, EXECUTION_STATE_FAILED)

    json_response = attachment.to_json()

    siemplify.result.add_result_json(json.dumps(json_response))

    output_message = "Successfully added attachment to the case."
    siemplify.end(output_message, True, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
