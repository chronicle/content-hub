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

import os
import pathlib
import shutil
import tempfile

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

DEST_DIR = "/opt/siemplify/siemplify_server/Scripting/FileUtilities/Archives"


def copy_files_to_temp_dir(archive_input):
    tmp_dir = tempfile.mkdtemp()
    for file in archive_input:
        shutil.copy2(file, tmp_dir)
    return tmp_dir


@output_handler
def main():
    siemplify = SiemplifyAction()

    archive_type = siemplify.extract_action_param("Archive Type", print_value=True)
    archive_input = list(
        filter(
            None,
            [
                x.strip()
                for x in siemplify.extract_action_param(
                    "Archive Input",
                    print_value=True,
                ).split(",")
            ],
        ),
    )
    archive_name = siemplify.extract_action_param("Archive Base Name", print_value=True)

    status = EXECUTION_STATE_COMPLETED
    output_message = (
        "output message :"
    )
    result_value = (
        None
    )

    # Does directory exist? If not, then create it.

    if not os.path.exists(DEST_DIR):
        try:
            pathlib.Path(DEST_DIR).mkdir(parents=True, exist_ok=True)
        except OSError:
            siemplify.LOGGER.error(f"Creation of the directory {DEST_DIR} failed")
            status = EXECUTION_STATE_FAILED

    try:
        archive_path = os.path.join(DEST_DIR, archive_name)

        if os.path.isdir(archive_input[0]):
            archive_output = shutil.make_archive(
                archive_path,
                archive_type,
                archive_input[0],
            )

        elif os.path.isfile(archive_input[0]):
            tmp_dir = copy_files_to_temp_dir(archive_input)
            archive_output = shutil.make_archive(archive_path, archive_type, tmp_dir)
            shutil.rmtree(tmp_dir)

        else:
            siemplify.LOGGER.error("Archive input is not file or directory.")
            raise Exception(
                "Unknown Input Type",
                "Archive input is not file or directory",
            )

        json_result = {"success": True, "archive": archive_output}
        result_value = archive_output
        siemplify.result.add_result_json(json_result)
        output_message = f"Successfully created archive: {archive_output}"
    except Exception as e:
        siemplify.LOGGER.error("General error performing action:\r")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n" + e
        raise

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
