from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.FileOperationManager import FileOperationManager
from soar_sdk.SiemplifyAction import *


@output_handler
def main():
    siemplify = SiemplifyAction()
    file_manager = FileOperationManager()
    source_file = siemplify.parameters["source_win_file_path"]
    dest_path = siemplify.parameters["dest_win_path"]
    keep_file = siemplify.parameters["keep_file"]
    dest_path = file_manager.transfer_file_win_to_win(source_file, dest_path, keep_file)

    output_message = f"Transfer File {source_file} to -> {dest_path} completed "
    siemplify.end(output_message, dest_path)


if __name__ == "__main__":
    main()
