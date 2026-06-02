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
from ..core.FileOperationManager import FileOperationManager
from soar_sdk.SiemplifyAction import *


@output_handler
def main():
    siemplify = SiemplifyAction()
    file_manager = FileOperationManager()
    source_linux_file = siemplify.parameters["source_linux_file_path"]
    source_linux_ip = siemplify.parameters["source_linux_ip"]
    source_linux_username = siemplify.parameters["source_linux_username"]
    source_linux_password = siemplify.parameters["source_linux_password"]
    dest_linux_path = siemplify.parameters["dest_linux_path"]
    dest_linux_ip = siemplify.parameters["dest_linux_ip"]
    dest_linux_username = siemplify.parameters["dest_linux_username"]
    dest_linux_password = siemplify.parameters["dest_linux_password"]
    keep_file = siemplify.parameters["keep_file"]
    dest_path = file_manager.transfer_file_unix_to_unix(
        source_linux_ip,
        source_linux_username,
        source_linux_password,
        source_linux_file,
        dest_linux_ip,
        dest_linux_username,
        dest_linux_password,
        dest_linux_path,
        keep_file,
    )

    output_message = (
        f"Transfer File {source_linux_file} to -> {dest_linux_path} completed "
    )
    siemplify.end(output_message, dest_path)


if __name__ == "__main__":
    main()
