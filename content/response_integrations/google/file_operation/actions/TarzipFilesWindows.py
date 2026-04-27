from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.FileOperationManager import FileOperationManager
from soar_sdk.SiemplifyAction import *


@output_handler
def main():
    siemplify = SiemplifyAction()
    file_manager = FileOperationManager()
    source_folder = siemplify.parameters["source_folder"]
    file_filter = siemplify.parameters["file_filter"]
    output_folder = siemplify.parameters["output_folder"]
    tarzip_file_path = file_manager.targz_windows(
        source_folder, file_filter, output_folder
    )

    output_message = f"Successfully created {tarzip_file_path}"
    siemplify.end(output_message, tarzip_file_path)


if __name__ == "__main__":
    main()
