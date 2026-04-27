from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SentinelOneManager import SentinelOneManager


# Consts.
SENTIAL_ONE_PROVIDER = "SentinelOne"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(SENTIAL_ONE_PROVIDER)
    sentinel_one_manager = SentinelOneManager(
        conf["Api Root"], conf["Username"], conf["Password"]
    )

    # Parameters.
    list_name = siemplify.parameters["List Name"]
    file_directory = siemplify.parameters["Path"]
    operation_system = siemplify.parameters["Operation System"]

    # Get system status.
    sentinel_one_manager.create_path_in_exclusion_list(
        list_name, file_directory, operation_system
    )

    # Form output message.
    output_message = f"Directory {list_name} added to exclusion list {file_directory}"

    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
