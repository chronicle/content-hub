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

from hashid import *
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

SUPPORTED_OUTPUT_TYPES = {"SHA-256", "MD5", "SHA-1", "SHA-512"}


@output_handler
def main():
    siemplify = SiemplifyAction()

    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = "Most likely hash types found"  # human readable message, showed in UI as the action result
    result_value = "true"  # Set a simple result value, used for playbook if\else and placeholders.

    res = []
    to_enrich = []
    hid = HashID()

    hashes = siemplify.parameters.get("Hashes")
    if hashes:
        hashes = hashes.split(",")
    try:
        for hash_ in hashes:
            intersection = list(
                {x.name for x in hid.identifyHash(hash_)}.intersection(
                    SUPPORTED_OUTPUT_TYPES,
                ),
            )
            if intersection:
                res.append({"Hash": hash_, "HashType": intersection[0]})
            else:
                res.append({"Hash": hash_, "HashType": "UNDETECTED"})

        for entity in siemplify.target_entities:
            if entity.entity_type == "FILEHASH":
                intersection = list(
                    {
                        x.name for x in hid.identifyHash(entity.identifier)}.intersection(SUPPORTED_OUTPUT_TYPES),
                )
                d = {"HashType": intersection[0]} if intersection else {"HashType": "UNDETECTED"}
                entity.additional_properties.update(d)
                to_enrich.append(entity)
                d["Hash"] = entity.identifier
                res.append(d)

        if to_enrich:
            siemplify.update_entities(to_enrich)

        siemplify.result.add_result_json(res)
        siemplify.result.add_json("Hash Types", res)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"Error: {e}"
        result_value = False

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
