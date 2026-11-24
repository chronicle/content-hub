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

from ..core.GoogleCloudComputeConstants import (
    INTEGRATION_NAME,
    ADD_NETWORK_TAGS_SCRIPT_NAME,
)
from ..core.GoogleCloudComputeGenerics import UpdateTagsAction


class AddNetworkTags(UpdateTagsAction):

    def _get_success_message(self, resource_path: str) -> str:
        return (
            "Successfully added network tags to the instance "
            f"{resource_path} in {INTEGRATION_NAME}."
        )

    def _get_tags(self, existing_tags: set[str]) -> list[str]:
        return list(existing_tags.union(self.params.network_tags_set))


def main() -> None:
    AddNetworkTags(
        f"{INTEGRATION_NAME} - {ADD_NETWORK_TAGS_SCRIPT_NAME}"
    ).run()


if __name__ == "__main__":
    main()
