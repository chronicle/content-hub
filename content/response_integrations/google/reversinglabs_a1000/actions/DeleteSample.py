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
from soar_sdk.SiemplifyDataModel import EntityTypes

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.A1000MalwareAnalysis import A1000MalwareAnalysisClient

# Consts
FILEHASH = EntityTypes.FILEHASH


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    conf = siemplify.get_configuration("ReversinglabsA1000")
    server_address = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]

    a1000_manager = A1000MalwareAnalysisClient(
        server_address,
        username,
        password
    )

    hashes = []

    for entity in siemplify.target_entities:
        if entity.entity_type == FILEHASH:
            result = a1000_manager.delete_sample(entity.identifier.lower())
            if result["code"] == 200:
                hashes.append(entity.identifier)

    if hashes:
        output_message = (
            "Following hashes deleted successfully from the A1000 appliance.\n\n"
        )
        output_message += ", ".join(hashes)
        result_value = True
    else:
        output_message = "No entities were deleted from the A1000 appliance."
        result_value = False

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
