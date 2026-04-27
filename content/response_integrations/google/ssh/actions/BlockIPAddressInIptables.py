from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import *
from ..core.SshManager import SshManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    server = siemplify.parameters.get("Remote Server")
    username = siemplify.parameters.get("Remote Username")
    password = siemplify.parameters.get("Remote Password")
    port = (
        int(siemplify.parameters.get("Remote Port"))
        if siemplify.parameters.get("Remote Port")
        else 22
    )
    ssh_wrapper = SshManager(server, username, password, port)

    output_message, status_code = ssh_wrapper.block_ip_in_iptables(
        siemplify.parameters["Block IP Address"]
    )
    if status_code == 0:
        results = "True"
    else:
        results = "False"
    siemplify.end(output_message, results)


if __name__ == "__main__":
    main()
