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
    server_ip = siemplify.parameters["server_ip"]
    username = siemplify.parameters["username"]
    password = siemplify.parameters["password"]
    source_folder = siemplify.parameters["source_folder"]
    file_filter = siemplify.parameters["file_filter"]
    output_folder = siemplify.parameters["output_folder"]
    tarzip_file_path = file_manager.targz_over_ssh_linux(
        server_ip, username, password, source_folder, file_filter, output_folder
    )

    output_message = f"Successfully created {tarzip_file_path}"
    siemplify.end(output_message, tarzip_file_path)


if __name__ == "__main__":
    main()
