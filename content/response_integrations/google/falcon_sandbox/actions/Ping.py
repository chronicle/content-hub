from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.FalconSandboxManager import FalconSandboxManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("FalconSandbox")
    server_address = configurations["Api Root"]
    key = configurations["Api Key"]

    falcon_manager = FalconSandboxManager(server_address, key)
    falcon_manager.test_connectivity()

    siemplify.end("Connected successfully.", "true")


if __name__ == "__main__":
    main()
