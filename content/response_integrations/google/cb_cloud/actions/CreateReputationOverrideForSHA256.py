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
import re

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.CBCloudManager import CBCloudManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from ..core.constants import (
    INTEGRATION_NAME,
    CREATE_REPUTATION_OVERRIDE_FOR_SHA256_SCRIPT_NAME,
    NOT_SPECIFIED,
    NEW_LINE,
    SHA256_REGEX,
    COMMASPACE,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_REPUTATION_OVERRIDE_FOR_SHA256_SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    org_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization Key",
        is_mandatory=True,
    )
    api_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API ID",
        is_mandatory=True,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    file_hash = extract_action_param(
        siemplify, param_name="SHA-256 Hash", is_mandatory=False, print_value=True
    )
    file_name = extract_action_param(
        siemplify, param_name="Filename", is_mandatory=True, print_value=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, print_value=True
    )
    reputation_override_list = extract_action_param(
        siemplify,
        param_name="Reputation Override List",
        is_mandatory=True,
        default_value=NOT_SPECIFIED,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, invalid_sha256_hashes, json_results = (
        [],
        [],
        [],
        {},
    )

    file_hashes = (
        [file_hash]
        if file_hash
        else [
            entity.identifier
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.FILEHASH
        ]
    )

    try:
        if reputation_override_list == NOT_SPECIFIED:
            raise Exception("Reputation Override List is not specified.")

        if not file_hashes:
            raise Exception(
                "Action failed to start since SHA-256 Hash was not provided either as Siemplify Entity or "
                "action input parameter."
            )
        invalid_sha256_hashes = [
            hash for hash in file_hashes if not re.search(SHA256_REGEX, hash)
        ]
        if invalid_sha256_hashes:
            siemplify.LOGGER.error(
                f"The following hashes are not SHA256 hashes: {COMMASPACE.join(invalid_sha256_hashes)}"
            )
            raise Exception(
                "Wrong hash format was provided. Action is working only with SHA-256 hashes."
            )

        manager = CBCloudManager(
            api_root=api_root,
            org_key=org_key,
            api_id=api_id,
            api_secret_key=api_secret_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        for file_hash in file_hashes:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) "
                    f"has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break
            try:
                siemplify.LOGGER.info(
                    f"Creating reputation override for hash: {file_hash}"
                )
                reputation = manager.create_sha256_reputation_override(
                    override_list=reputation_override_list,
                    sha256_hash=file_hash,
                    filename=file_name,
                    description=description,
                )
                json_results[file_hash] = reputation.to_json()
                successful_entities.append(file_hash)
                siemplify.LOGGER.info(f"Finished processing entity: {file_hash}")
            except Exception as e:
                failed_entities.append(file_hash)
                siemplify.LOGGER.error(f"An error occurred on entity: {file_hash}")
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = "Successfully created reputation override for the following entities:\n   {}".format(
                f"{NEW_LINE}   ".join(successful_entities)
            )
            result_value = True
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            if failed_entities:
                output_message += "Action failed to to create reputation override for the following entities:\n   {}".format(
                    f"{NEW_LINE}   ".join(failed_entities)
                )
        else:
            output_message = "No reputation overrides were created."

    except Exception as e:
        output_message = f"Error executing action {CREATE_REPUTATION_OVERRIDE_FOR_SHA256_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
