from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.CertlyManager import CertlyManager
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Certly")
    api_token = conf["Api Token"]
    api_url = conf["Api Root"]
    certly = CertlyManager(api_token, api_url)

    connectivity = certly.test_connectivity()
    output_message = "Connected Successfully"
    siemplify.end(output_message, connectivity)


if __name__ == "__main__":
    main()
