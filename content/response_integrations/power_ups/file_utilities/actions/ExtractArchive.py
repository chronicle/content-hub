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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

DEST_DIR = "/opt/siemplify/siemplify_server/Scripting/FileUtilities/Extract"


def path_to_dict(path):
    d = {"name": os.path.basename(path)}
    filename, file_extension = os.path.splitext(path)
    if os.path.isdir(path):
        d["type"] = "directory"
        d["children"] = [path_to_dict(os.path.join(path, x)) for x in os.listdir(path)]
    else:
        d["type"] = "file"
        d["extension"] = file_extension
        d["path"] = path
    return d


@output_handler
def main():
    siemplify = SiemplifyAction()
    archives = list(
        filter(
            None,
            [x.strip() for x in siemplify.parameters.get("Archive").split(",")],
        ),
    )

    status = EXECUTION_STATE_COMPLETED
    output_message = (
        "output message :"
    )
    result_value = (
        None
    )
    json_result = {}
    success_files = []
    failed_files = []
    json_result["archives"] = []
    for archive in archives:
        archive_name = pathlib.Path(archive).stem
        full_archive_name = pathlib.Path(archive).name

        output_dir = os.path.join(DEST_DIR, archive_name)
        if not os.path.exists(output_dir):
            try:
                pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
            except OSError:
                siemplify.LOGGER.error(f"Creation of the directory {output_dir} failed")
                status = EXECUTION_STATE_FAILED
                json_result["archives"].append(
                    {"success": False, "archive": full_archive_name},
                )
                failed_files.append(archive)
                raise
        try:
            files = shutil.unpack_archive(archive, output_dir)
            files = path_to_dict(output_dir)
            files_w_path = [
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, f))
            ]
            onlyfiles = [
                f
                for f in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, f))
            ]
            json_result["archives"].append(
                {
                    "success": True,
                    "archive": full_archive_name,
                    "folder": output_dir,
                    "files": files,
                    "files_with_path": files_w_path,
                    "files_list": onlyfiles,
                },
            )
            output_message = f"\nSuccessfully extracted archive: {full_archive_name}"
            success_files.append(archive)
        except Exception as e:
            siemplify.LOGGER.error("General error performing action:\r")
            siemplify.LOGGER.exception(e)
            status = EXECUTION_STATE_FAILED
            result_value = "Failed"
            output_message += "\n" + e
            json_result["archives"].append(
                {"success": False, "archive": full_archive_name},
            )
            failed_files.append(archive)
            raise
    if not failed_files:
        result_value = True
    siemplify.result.add_result_json(json_result)
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
