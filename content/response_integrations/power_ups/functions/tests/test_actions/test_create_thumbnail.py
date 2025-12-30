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

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import CreateThumbnail


@set_metadata(
    integration_config={},
    parameters={
        "Base64 Image": (
            # base64 encoded string of a 1x1 transparent PNG image
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C"
            "8AAAAASUVORK5CYII="
        ),
        "Thumbnail Size": "2, 2",
        "Image Key Path": "",
    },
)
def test_create_thumbnail_json_result(action_output: MockActionOutput) -> None:
    CreateThumbnail.main()

    assert action_output.report.json_output.json_result == {
        "thumbnail": (
            "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAC0lEQVR4nGNggAEAAAoAAX"
            "+AdF4AAAAASUVORK5CYII="
        )
    }
    assert action_output.report.execution_state == ExecutionState.COMPLETED
