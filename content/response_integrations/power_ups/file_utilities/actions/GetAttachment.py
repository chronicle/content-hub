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
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_attachments_metadata

CASE_EVIDENCE_ID: str = "evidenceId"


@output_handler
def main():
    siemplify = SiemplifyAction()
    scope = siemplify.parameters.get("Attachment Scope")
    attachments_metadata = [
        attachment.to_json() for attachment in
        get_attachments_metadata(siemplify, siemplify.case.identifier)
    ]
    attachments = []
    for wall_item in attachments_metadata:
        if wall_item["type"] == 4:
            if scope.lower() == "alert":
                if siemplify.current_alert.identifier == wall_item["alertIdentifier"]:
                    attachments.append(wall_item)
            else:
                attachments.append(wall_item)

    for attachment in attachments:
        attachment_record = siemplify.get_attachment(attachment[CASE_EVIDENCE_ID])
        attachment_content = attachment_record.getvalue()
        b64 = base64.b64encode(attachment_content)
        attachment["base64_blob"] = b64.decode("ascii")

    siemplify.result.add_result_json(json.dumps(attachments))

    siemplify.end(f"{len(attachments)} attachment(s) found", len(attachments))


if __name__ == "__main__":
    main()
