from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ProofPointPSManager import ProofPointPSManager


PROVIDER = "ProofPointPS"
ACTION_NAME = "ProofPointPS - Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.action_definition_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)
    verify_ssl = conf.get("Verify SSL").lower() == "true"
    proofpoint_manager = ProofPointPSManager(
        server_address=conf.get("Api Root"),
        username=conf.get("Username"),
        password=conf.get("Password"),
        verify_ssl=verify_ssl,
    )

    proofpoint_manager.test_connectivity()

    siemplify.end("Connection Established", True)


if __name__ == "__main__":
    main()
