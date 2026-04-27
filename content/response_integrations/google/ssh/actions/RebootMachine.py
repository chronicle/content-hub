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

    status_code = ssh_wrapper.reboot()
    if status_code == -1:
        results = "True"
        output_message = "Successfully reboot remote server"
    else:
        results = "False"
        output_message = "Failed to reboot remote server"
    siemplify.end(output_message, results)


if __name__ == "__main__":
    main()
