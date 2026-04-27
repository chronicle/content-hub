from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.FileOperationManager import FileOperationManager
from soar_sdk.SiemplifyAction import *


@output_handler
def main():
    siemplify = SiemplifyAction()
    file_manager = FileOperationManager()
    source_win_file = siemplify.parameters["source_win_file_path"]
    dest_linux_path = siemplify.parameters["dest_linux_path"]
    dest_linux_ip = siemplify.parameters["dest_linux_ip"]
    dest_linux_username = siemplify.parameters["dest_linux_username"]
    dest_linux_password = siemplify.parameters["dest_linux_password"]
    keep_file = siemplify.parameters["keep_file"]
    dest_path = file_manager.transfer_file_win_to_unix(
        source_win_file,
        dest_linux_ip,
        dest_linux_username,
        dest_linux_password,
        dest_linux_path,
        keep_file,
    )

    output_message = (
        f"Transfer File {source_win_file} to -> {dest_linux_path} completed "
    )
    siemplify.end(output_message, dest_path)


if __name__ == "__main__":
    main()
