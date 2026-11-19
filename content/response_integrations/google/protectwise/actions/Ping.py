from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from protectwise.core.ProtectwiseManager import ProtectwiseManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("Protectwise")
    username = configurations["Email"]
    password = configurations["Password"]

    # If no exception occurs - then connection is successfull
    protectwise_manager = ProtectwiseManager(username, password)

    siemplify.end("Connected successfully.", "true")


if __name__ == "__main__":
    main()
