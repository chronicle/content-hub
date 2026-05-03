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
import os
from ..core.LogRhythmManager import LogRhythmRESTManager, FILE_TYPE, COMPLETED_STATUS
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, DOWNLOAD_CASE_FILES_SCRIPT_NAME
from ..core.utils import save_attachment, validate_local_path

EXTENSION_SPLITTER = "."


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_CASE_FILES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    case_id = extract_action_param(
        siemplify, param_name="Case ID", is_mandatory=True, print_value=True
    )
    folder_path = extract_action_param(
        siemplify,
        param_name="Download Folder Path",
        is_mandatory=True,
        print_value=True,
    )
    overwrite = extract_action_param(
        siemplify,
        param_name="Overwrite",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = (f"Successfully downloaded files related to case with ID "
                      f"{case_id} in {INTEGRATION_NAME}.")
    successful_filenames = []
    json_result = {"absolute_file_paths": []}

    try:
        validate_local_path(folder_path)

        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        case_evidences = manager.get_case_evidence(
            case_id=case_id, status_filter=COMPLETED_STATUS, type_filter=FILE_TYPE
        )

        if not overwrite:
            already_existing_files = get_existing_filenames(case_evidences, folder_path)
            if already_existing_files:
                raise Exception(
                    f"files with path {', '.join(already_existing_files)} already "
                    f"exist. Please delete the files or set 'Overwrite' to true."
                )

        for evidence in case_evidences:
            file_name = construct_download_filename(evidence)
            file_content = manager.download_file_evidence(
                case_id=case_id, evidence_id=evidence.id
            )
            save_attachment(path=folder_path, name=file_name, content=file_content)
            successful_filenames.append(file_name)
            if (
                os.path.join(folder_path, file_name)
                not in json_result["absolute_file_paths"]
            ):
                json_result["absolute_file_paths"].append(
                    os.path.join(folder_path, file_name)
                )

        if not successful_filenames:
            output_message = (f"No related files were found for the case with ID "
                              f"{case_id} in {INTEGRATION_NAME}.")
            result_value = False

        siemplify.result.add_result_json(json_result)

    except Exception as e:
        output_message = (
            f"Error executing action '{DOWNLOAD_CASE_FILES_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"is_success: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def get_existing_filenames(evidences, path):
    existing_filenames = []
    filenames = [construct_download_filename(evidence) for evidence in evidences]
    for filename in filenames:
        filepath = os.path.join(path, filename)
        if os.path.exists(filepath):
            existing_filenames.append(filepath)

    return existing_filenames


def construct_download_filename(evidence):
    if EXTENSION_SPLITTER in evidence.filename:
        return (
            f"{evidence.filename.split(EXTENSION_SPLITTER)[0]}_{evidence.filesize}"
            f"{EXTENSION_SPLITTER}{evidence.filename.split(EXTENSION_SPLITTER)[1]}"
        )

    return f"{evidence.filename}_{evidence.filesize}"


if __name__ == "__main__":
    main()
