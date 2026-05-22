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
from typing import Any

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AttachmentsManager import AttachmentsManager, ExecutionScope


@output_handler
def main() -> None:
    siemplify: SiemplifyAction = SiemplifyAction()
    scope: str = siemplify.parameters.get("Attachment Scope")

    execution_scope: Any = getattr(
        siemplify,
        "execution_scope",
        ExecutionScope.Alert,
    )
    siemplify.LOGGER.info(f"Running in {execution_scope.name.lower()} scope")

    attach_mgr: AttachmentsManager = AttachmentsManager(siemplify=siemplify)

    attachments: list[Any] = attach_mgr.get_attachments_by_scope(
        execution_scope=execution_scope,
        attachment_scope_param=scope,
    )

    attachments = attach_mgr.get_attachment_blobs(attachments)

    siemplify.result.add_result_json(json.dumps(attachments))

    siemplify.end(f"{len(attachments)} attachment(s) found", len(attachments))


if __name__ == "__main__":
    main()
