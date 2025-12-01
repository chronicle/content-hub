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

import io
import zipfile

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from ..core.AttachmentsManager import AttachmentsManager

INTEGRATION_NAME = "FileUtilities"
ACTION_NAME = "Extract Zip Files"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    include_data = (
        siemplify.extract_action_param(
            "Include Data In JSON Result",
            print_value=True,
        ).lower()
        == "true"
    )
    bruteforce_password = (
        siemplify.extract_action_param("BruteForce Password", print_value=True).lower()
        == "true"
    )
    create_entities = (
        siemplify.extract_action_param("Create Entities", print_value=True).lower()
        == "true"
    )
    add_to_case_wall = (
        siemplify.extract_action_param("Add to Case Wall", print_value=True).lower()
        == "true"
    )

    zip_passwords = list(
        filter(
            None,
            [
                x.strip()
                for x in siemplify.extract_action_param(
                    "Zip File Password",
                    default_value="",
                ).split(
                    siemplify.extract_action_param(
                        "Zip Password List Delimiter",
                        print_value=True,
                    ),
                )
            ],
        ),
    )
    status = EXECUTION_STATE_COMPLETED
    output_message = (
        "output message :"  # human readable message, showed in UI as the action result
    )
    result_value = "false"  # Set a simple result value, used for playbook if\else and placeholders.
    attach_mgr = AttachmentsManager(siemplify=siemplify)

    extracted_files = {}
    for entity in siemplify.target_entities:
        if entity.entity_type == "FILENAME":
            siemplify.LOGGER.info(
                f"The entity {entity.identifier} is being checked for being zip",
            )
            if "attachment_id" in entity.additional_properties:
                _attachment = siemplify.get_attachment(
                    entity.additional_properties["attachment_id"],
                )
                zip_file_content = io.BytesIO(_attachment.getvalue())
                if zipfile.is_zipfile(zip_file_content):
                    extracted_files[entity.identifier] = attach_mgr.extract_zip(
                        entity.identifier,
                        zip_file_content,
                        bruteforce=bruteforce_password,
                        pwds=zip_passwords,
                    )
                    result_value = "true"

    if add_to_case_wall:
        for file_name in extracted_files:
            for x_file in extracted_files[file_name]:
                if x_file["filename"].endswith("/") or not x_file.get("raw", ""):
                    siemplify.LOGGER.info(
                        "Skipping directory or empty file: "
                        f"{x_file['filename']} from case wall.",
                    )
                    continue
                siemplify.LOGGER.info(
                    f"Adding the file: {x_file['filename']} to the case wall",
                )
                attachment_res = attach_mgr.add_attachment(
                    x_file["filename"],
                    x_file["raw"],
                    siemplify.case_id,
                    siemplify.alert_id,
                )
                x_file["attachment_id"] = attachment_res

    if not include_data:
        for file_name in extracted_files:
            for x_file in extracted_files[file_name]:
                del x_file["raw"]

    if create_entities:
        for file_name in extracted_files:
            siemplify.result.add_json(file_name, extracted_files[file_name], "Zip File")
            attach_mgr.create_file_entities(extracted_files[file_name])

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(extracted_files))
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
